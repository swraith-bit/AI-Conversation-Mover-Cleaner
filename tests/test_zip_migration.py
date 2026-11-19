"""Tests for fast atomic ZIP handling, corruption safety, and progress reporting."""

import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import core.chat_migrator as cm
import core.paths as cp
from core.zip_utils import (
    atomic_zip_write,
    collect_dir_entries,
    compression_for,
    extract_zip_with_progress,
    snapshot_sqlite_db,
    write_entries_to_zip,
)


class ZipUtilsAndMigrationTests(unittest.TestCase):
    def test_compression_for_skips_incompressible(self):
        self.assertEqual(compression_for(Path("shot.png")), zipfile.ZIP_STORED)
        self.assertEqual(compression_for(Path("nested.zip")), zipfile.ZIP_STORED)
        self.assertEqual(compression_for(Path("transcript.jsonl")), zipfile.ZIP_DEFLATED)

    def test_atomic_zip_write_cleans_tmp_on_error(self):
        with tempfile.TemporaryDirectory() as td:
            out_zip = Path(td) / "out.zip"
            with self.assertRaises(RuntimeError):
                def _fail(zf):
                    zf.writestr("a.txt", "partial")
                    raise RuntimeError("boom")
                atomic_zip_write(out_zip, _fail)

            self.assertFalse(out_zip.exists())
            self.assertEqual(list(Path(td).glob("*.tmp")), [])

    def test_chunked_write_extract_and_progress(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src_dir = root / "src"
            src_dir.mkdir()
            (src_dir / "empty.txt").write_bytes(b"")
            (src_dir / "img.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 1024)
            big_data = b"hello world!\n" * 200_000  # ~2.6 MB
            (src_dir / "big.jsonl").write_bytes(big_data)

            out_zip = root / "pack.zip"
            write_events = []
            entries = collect_dir_entries(src_dir, "data")
            atomic_zip_write(
                out_zip,
                lambda zf: write_entries_to_zip(zf, entries, progress_callback=lambda d, t: write_events.append((d, t))),
            )

            self.assertTrue(write_events)
            self.assertEqual(write_events[-1][0], write_events[-1][1])

            with zipfile.ZipFile(out_zip, "r") as zf:
                self.assertIsNone(zf.testzip())
                self.assertEqual(zf.getinfo("data/img.png").compress_type, zipfile.ZIP_STORED)
                self.assertEqual(zf.getinfo("data/big.jsonl").compress_type, zipfile.ZIP_DEFLATED)

            ext_dir = root / "ext"
            read_events = []
            extract_zip_with_progress(out_zip, ext_dir, progress_callback=lambda d, t: read_events.append((d, t)))
            self.assertTrue(read_events)
            self.assertEqual(read_events[-1][0], read_events[-1][1])
            self.assertEqual((ext_dir / "data" / "big.jsonl").read_bytes(), big_data)
            self.assertEqual((ext_dir / "data" / "empty.txt").read_bytes(), b"")

    def test_snapshot_sqlite_db_in_wal_mode(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db_path = root / "live.db"
            conn = sqlite3.connect(str(db_path))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, val TEXT)")
            conn.execute("INSERT INTO t VALUES (1, 'ok')")
            conn.commit()
            try:
                snap_dir = root / "snap_out"
                snap_dir.mkdir()
                snap = snapshot_sqlite_db(db_path, snap_dir)
                s_conn = sqlite3.connect(str(snap))
                rows = s_conn.execute("SELECT id, val FROM t").fetchall()
                s_conn.close()
                self.assertEqual(rows, [(1, "ok")])
            finally:
                conn.close()

    def test_corrupted_zip_does_not_wipe_existing_chats(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bad_zip = root / "corrupt.zip"
            bad_zip.write_bytes(b"not a valid zip payload")

            clean_mock = mock.Mock()
            with mock.patch.object(cm, "clean_all_conversations_and_projects", clean_mock):
                ok, msg = cm.import_chats_and_projects(bad_zip, mode="replace")

            self.assertFalse(ok)
            self.assertIn("corrupted", msg.lower())
            clean_mock.assert_not_called()

    def test_export_and_import_antigravity_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            agy_dir = root / ".gemini" / "antigravity"
            convos = agy_dir / "conversations"
            brain = agy_dir / "brain" / "c1"
            cfg_prj = root / ".gemini" / "config" / "projects"
            convos.mkdir(parents=True)
            brain.mkdir(parents=True)
            cfg_prj.mkdir(parents=True)

            sum_db = agy_dir / "conversation_summaries.db"
            conn = sqlite3.connect(str(sum_db))
            conn.execute(
                "CREATE TABLE conversation_summaries (id TEXT PRIMARY KEY, project_path_encoded TEXT, project_root_path_encoded TEXT, title TEXT)"
            )
            conn.execute("INSERT INTO conversation_summaries VALUES ('c1', 'C:/Users/Alice/proj', 'C:/Users/Alice/proj', 'Test')")
            conn.commit()
            conn.close()

            (convos / "c1.pb").write_bytes(b"proto-bytes")
            (brain / "note.md").write_text("Path: C:/Users/Alice/proj", encoding="utf-8")
            (cfg_prj / "p.json").write_text(json.dumps({"path": "C:/Users/Alice/proj"}), encoding="utf-8")
            p_json = root / ".gemini" / "projects.json"
            p_json.write_text(json.dumps({"projects": {"p1": "C:/Users/Alice/proj"}}), encoding="utf-8")

            zip_path = root / "export.zip"
            progress_pts = []
            with mock.patch.multiple(
                cm,
                is_antigravity_running=lambda: False,
                get_summaries_db=lambda: sum_db,
                get_proto_summaries=lambda: agy_dir / "missing.pb",
                get_conversations_dir=lambda: convos,
                get_brain_dir=lambda: agy_dir / "brain",
                get_config_projects_dir=lambda: cfg_prj,
                get_projects_json=lambda: p_json,
                get_app_storage_json=lambda: root / "missing_app_storage.json",
                get_user_home=lambda: Path("C:/Users/Alice"),
                get_system_stats=lambda: {"convo_count": 1, "project_count": 1, "total_chat_size_mb": 0.1},
            ):
                ok, _ = cm.export_chats_and_projects(zip_path, progress_callback=lambda d, t: progress_pts.append((d, t)))
                self.assertTrue(ok)
                self.assertTrue(zip_path.exists())
                self.assertTrue(progress_pts and progress_pts[-1][0] == progress_pts[-1][1])

            # Import into a fresh target home Bob
            tgt = root / "bob_target"
            t_agy = tgt / ".gemini" / "antigravity"
            t_convos = t_agy / "conversations"
            t_brain = t_agy / "brain"
            t_cfg_prj = tgt / ".gemini" / "config" / "projects"
            t_sum_db = t_agy / "conversation_summaries.db"
            t_p_json = tgt / ".gemini" / "projects.json"

            with mock.patch.multiple(
                cm,
                is_antigravity_running=lambda: False,
                get_summaries_db=lambda: t_sum_db,
                get_proto_summaries=lambda: t_agy / "missing.pb",
                get_conversations_dir=lambda: t_convos,
                get_brain_dir=lambda: t_brain,
                get_config_projects_dir=lambda: t_cfg_prj,
                get_projects_json=lambda: t_p_json,
                get_app_storage_json=lambda: tgt / "missing_app_storage.json",
                get_user_home=lambda: Path("C:/Users/Bob"),
                clean_all_conversations_and_projects=lambda **kw: (True, "ok"),
            ):
                ok, msg = cm.import_chats_and_projects(zip_path, mode="replace", remap_paths=True)
                self.assertTrue(ok, msg)

            self.assertEqual((t_convos / "c1.pb").read_bytes(), b"proto-bytes")
            self.assertEqual((t_brain / "c1" / "note.md").read_text(encoding="utf-8"), "Path: C:/Users/Bob/proj")
            self.assertIn("C:/Users/Bob/proj", t_p_json.read_text(encoding="utf-8"))

    def test_custom_agent_dir_overrides_and_reset(self):
        with tempfile.TemporaryDirectory() as td:
            custom_gemini = Path(td) / "custom_gemini"
            custom_claude = Path(td) / "custom_claude"
            custom_codex = Path(td) / "custom_codex"
            try:
                cp.set_custom_agent_dirs({
                    "antigravity": str(custom_gemini),
                    "claude": str(custom_claude),
                    "codex": str(custom_codex),
                })
                self.assertEqual(cp.get_gemini_dir(), custom_gemini)
                self.assertEqual(cp.get_conversations_dir(), custom_gemini / "antigravity" / "conversations")
                self.assertEqual(cp.get_claude_projects_dir(), custom_claude / "projects")
                self.assertEqual(cp.get_codex_sessions_dir(), custom_codex / "sessions")
            finally:
                cp.set_custom_agent_dirs(None)

            self.assertEqual(cp.get_gemini_dir(), cp.get_default_agent_dir("antigravity"))


if __name__ == "__main__":
    unittest.main()
