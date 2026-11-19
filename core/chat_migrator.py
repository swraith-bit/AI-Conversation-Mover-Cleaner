"""
chat_migrator.py - Antigravity, Claude Code ve OpenAI Codex sohbet/oturum taşıma (Export/Import) motoru.
Farklı bilgisayarlardaki kullanıcı yollarını (Path Remapping) otomatik uyarlar.
"""

import os
import re
import json
import zlib
import shutil
import sqlite3
import tempfile
import zipfile
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Callable, Optional, Tuple, List

from core.zip_utils import (
    atomic_zip_write,
    collect_dir_entries,
    extract_zip_with_progress,
    fs_path,
    snapshot_sqlite_db,
    write_entries_to_zip,
)

from core.paths import (
    get_summaries_db,
    get_proto_summaries,
    get_conversations_dir,
    get_brain_dir,
    get_config_projects_dir,
    get_projects_json,
    get_app_storage_json,
    is_antigravity_running,
    close_antigravity_processes,
    get_claude_dir,
    get_claude_projects_dir,
    get_claude_history_file,
    get_claude_settings_file,
    is_claude_running,
    close_claude_processes,
    get_codex_dir,
    get_codex_sessions_dir,
    get_codex_history_dir,
    get_codex_config_file,
    is_codex_running,
    close_codex_processes,
    get_user_home,
    get_system_stats,
    get_claude_stats,
    get_codex_stats
)
from core.cleaner import (
    clean_all_conversations_and_projects,
    clean_claude_conversations,
    clean_codex_conversations
)


def _to_file_uri(path_str: str) -> str:
    """Windows dosya yolunu file:///c%3A/... URI formatına dönüştürür."""
    norm = path_str.replace("\\", "/")
    if len(norm) > 1 and norm[1] == ":":
        drive = norm[0].lower()
        rest = norm[2:]
        encoded_rest = urllib.parse.quote(rest, safe="/")
        return f"file:///{drive}%3A{encoded_rest}"
    return f"file://{urllib.parse.quote(norm, safe='/')}"


def remap_paths_in_text(text: str, source_home: str, target_home: str) -> str:
    """Metin içindeki kaynak kullanıcı yollarını hedef kullanıcı yollarıyla değiştirir."""
    if not source_home or source_home == target_home:
        return text

    # 1. Normal Windows ve POSIX yolları
    s_norm = source_home.replace("\\", "/")
    t_norm = target_home.replace("\\", "/")
    text = text.replace(s_norm, t_norm)
    text = text.replace(source_home, target_home)

    # 2. URI biçimleri (küçük ve büyük harf sürücü varyasyonları)
    s_uri = _to_file_uri(source_home)
    t_uri = _to_file_uri(target_home)
    
    # Küçük sürücü harfi (file:///c%3A ve file:///c:)
    text = text.replace(s_uri, t_uri)
    text = text.replace(s_uri.replace("%3A", ":"), t_uri.replace("%3A", ":"))

    # Büyük sürücü harfi (file:///C%3A ve file:///C:)
    if len(s_norm) > 1 and s_norm[1] == ":":
        s_drive = s_norm[0]
        t_drive = t_norm[0]
        s_uri_upper = s_uri.replace(f"file:///{s_drive.lower()}", f"file:///{s_drive.upper()}")
        t_uri_upper = t_uri.replace(f"file:///{t_drive.lower()}", f"file:///{t_drive.upper()}")
        text = text.replace(s_uri_upper, t_uri_upper)
        text = text.replace(s_uri_upper.replace("%3A", ":"), t_uri_upper.replace("%3A", ":"))

    return text


def _remap_claude_folder_name(folder_name: str, source_home: str, target_home: str) -> str:
    """Claude Code'un -C-Users-EskiAd- formatındaki proje klasör isimlerini yeni kullanıcı adına uyarlar."""
    if not source_home or source_home == target_home:
        return folder_name

    s_slug = re.sub(r"[^a-zA-Z0-9]", "-", source_home.strip("\\/"))
    t_slug = re.sub(r"[^a-zA-Z0-9]", "-", target_home.strip("\\/"))

    if s_slug in folder_name:
        return folder_name.replace(s_slug, t_slug)

    # Basit kullanıcı adı değişimi
    s_user = Path(source_home).name
    t_user = Path(target_home).name
    if s_user and t_user and s_user in folder_name:
        return folder_name.replace(s_user, t_user)

    return folder_name


# ==============================================================================
# 1. ANTIGRAVITY SOHBET & PROJE TAŞIMA
# ==============================================================================

def export_chats_and_projects(
    output_zip_path: Path,
    log: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Tuple[bool, str]:
    """Tüm Antigravity sohbetlerini, veritabanlarını ve projelerini zip paketine aktarır."""
    def _log(msg: str):
        if log:
            log(msg)

    if is_antigravity_running():
        _log("ℹ️ Antigravity açık durumda. Sohbetler canlı durumdayken güvenle okunup paketleniyor...")

    _log(f"📦 Antigravity dışa aktarma başlatılıyor: {output_zip_path.name}")
    output_zip_path.parent.mkdir(parents=True, exist_ok=True)

    stats = get_system_stats()
    _log(f"  Bulunan sohbet sayısı: {stats['convo_count']} (Boyut: ~{stats['total_chat_size_mb']} MB)")

    try:
        with tempfile.TemporaryDirectory(prefix="agm_agy_exp_") as snap_dir_str:
            snap_dir = Path(snap_dir_str)
            entries: List[Tuple[Path, str, int]] = []

            sum_db = get_summaries_db()
            if sum_db.exists():
                snap_db = snapshot_sqlite_db(sum_db, snap_dir)
                entries.append((snap_db, "antigravity/conversation_summaries.db", snap_db.stat().st_size))

            proto = get_proto_summaries()
            if proto.exists() and proto.is_file():
                entries.append((proto, "antigravity/agyhub_summaries_proto.pb", proto.stat().st_size))

            convos_dir = get_conversations_dir()
            if convos_dir.exists():
                for f in convos_dir.glob("*"):
                    if f.is_file():
                        entries.append((f, f"antigravity/conversations/{f.name}", f.stat().st_size))

            brain_dir = get_brain_dir()
            if brain_dir.exists():
                entries.extend(collect_dir_entries(brain_dir, "antigravity/brain"))

            prj_dir = get_config_projects_dir()
            if prj_dir.exists():
                for f in prj_dir.glob("*.json"):
                    if f.is_file():
                        entries.append((f, f"config/projects/{f.name}", f.stat().st_size))

            p_json = get_projects_json()
            if p_json.exists() and p_json.is_file():
                entries.append((p_json, "projects.json", p_json.stat().st_size))

            def _write_archive(zf: zipfile.ZipFile):
                write_entries_to_zip(zf, entries, progress_callback=progress_callback, log=log)

                app_st = get_app_storage_json()
                if app_st.exists():
                    try:
                        with open(app_st, "r", encoding="utf-8") as asf:
                            raw_data = json.load(asf)
                        filtered = {
                            "projectsOrder": raw_data.get("projectsOrder", "[]"),
                            "lastCreatedProjectId": raw_data.get("lastCreatedProjectId", ""),
                            "comments": raw_data.get("comments", "{}")
                        }
                        for k, v in raw_data.items():
                            if k.startswith("antigravity-multi-conversation-layout-v3-"):
                                filtered[k] = v
                        zf.writestr("app_storage_partial.json", json.dumps(filtered, indent=2))
                    except Exception:
                        pass

                manifest = {
                    "version": "1.0",
                    "export_type": "antigravity_chats_and_projects",
                    "created_at": datetime.now().isoformat(),
                    "source_user_home": str(get_user_home()),
                    "source_username": get_user_home().name,
                    "convo_count": stats["convo_count"],
                    "project_count": stats["project_count"]
                }
                zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            atomic_zip_write(output_zip_path, _write_archive)

        _log(f"✅ Antigravity dışa aktarma tamamlandı: {output_zip_path.name}")
        return True, "Antigravity sohbet ve projeleri başarıyla dışa aktarıldı."
    except Exception as e:
        err = f"Dışa aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


def import_chats_and_projects(
    input_zip_path: Path,
    mode: str = "replace",
    remap_paths: bool = True,
    log: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Tuple[bool, str]:
    """Antigravity yedek paketini sisteme yükler."""
    def _log(msg: str):
        if log:
            log(msg)

    if not input_zip_path.exists():
        return False, f"Yedek dosyası bulunamadı: {input_zip_path}"

    _log(f"📥 Antigravity içe aktarma başlatılıyor: {input_zip_path.name} (Mod: {mode.upper()})")

    try:
        with tempfile.TemporaryDirectory(prefix="agm_agy_imp_") as temp_dir_str:
            temp_extract = Path(temp_dir_str)

            # Validate & extract first before modifying or wiping existing user data
            _log("  🔍 ZIP arşivi doğrulanıyor ve açılıyor...")
            extract_zip_with_progress(input_zip_path, temp_extract, progress_callback=progress_callback)

            manifest = {}
            manifest_path = temp_extract / "manifest.json"
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    _log(f"  Kaynak sistem: {manifest.get('source_username', 'Bilinmeyen')} ({manifest.get('source_user_home', '')})")
                except Exception:
                    pass

            source_home = manifest.get("source_user_home", "")
            target_home = str(get_user_home())

            if remap_paths and source_home and source_home != target_home:
                _log(f"  🔄 Yol uyarlama aktif: {source_home} ➔ {target_home}")

            if is_antigravity_running():
                _log("⚠️ Antigravity açık tespit edildi, kapatılıyor...")
                close_antigravity_processes()

            if mode == "replace":
                _log("  🧹 Temiz kurulum: Mevcut veriler sıfırlanıyor...")
                clean_all_conversations_and_projects(take_backup=True, force_close=True, log=log)

            # A) conversations/
            temp_convos = temp_extract / "antigravity" / "conversations"
            target_convos = get_conversations_dir()
            target_convos.mkdir(parents=True, exist_ok=True)
            if temp_convos.exists():
                convo_count = 0
                for cf in temp_convos.glob("*"):
                    if cf.is_file():
                        dst = target_convos / cf.name
                        shutil.copy2(fs_path(cf), fs_path(dst))
                        convo_count += 1
                _log(f"  ✓ {convo_count} adet sohbet veritabanı kopyalandı.")

            # B) brain/
            temp_brain = temp_extract / "antigravity" / "brain"
            target_brain = get_brain_dir()
            target_brain.mkdir(parents=True, exist_ok=True)
            if temp_brain.exists():
                brain_dirs_count = 0
                for sub in temp_brain.iterdir():
                    if sub.is_dir():
                        dst_dir = target_brain / sub.name
                        if dst_dir.exists():
                            shutil.rmtree(fs_path(dst_dir), ignore_errors=True)
                        shutil.copytree(fs_path(sub), fs_path(dst_dir))
                        brain_dirs_count += 1

                        if remap_paths and source_home and source_home != target_home:
                            for root, _, files in os.walk(fs_path(dst_dir)):
                                for fn in files:
                                    if fn.endswith((".json", ".jsonl", ".txt", ".md", ".log")):
                                        fp = Path(root) / fn
                                        try:
                                            raw = Path(fs_path(fp)).read_text(encoding="utf-8", errors="ignore")
                                            remapped = remap_paths_in_text(raw, source_home, target_home)
                                            if raw != remapped:
                                                Path(fs_path(fp)).write_text(remapped, encoding="utf-8")
                                        except Exception:
                                            pass
                _log(f"  ✓ {brain_dirs_count} adet hafıza/log dizini (brain) aktarıldı.")

            # C) conversation_summaries.db
            temp_db = temp_extract / "antigravity" / "conversation_summaries.db"
            target_db = get_summaries_db()
            if temp_db.exists():
                if mode == "replace" or not target_db.exists():
                    target_db.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(temp_db, target_db)
                    if remap_paths and source_home and source_home != target_home:
                        _remap_antigravity_sqlite(target_db, source_home, target_home)
                    _log("  ✓ conversation_summaries.db yüklendi ve yollar uyarlandı.")
                elif mode == "merge":
                    _merge_antigravity_summaries(temp_db, target_db, source_home, target_home if remap_paths else None, log)

            # D) agyhub_summaries_proto.pb
            proto = get_proto_summaries()
            if proto.exists():
                try:
                    proto.unlink()
                except Exception:
                    pass

            # E) config/projects
            temp_prj = temp_extract / "config" / "projects"
            target_prj = get_config_projects_dir()
            target_prj.mkdir(parents=True, exist_ok=True)
            if temp_prj.exists():
                for pf in temp_prj.glob("*.json"):
                    dst = target_prj / pf.name
                    try:
                        content = pf.read_text(encoding="utf-8", errors="ignore")
                        if remap_paths and source_home and source_home != target_home:
                            content = remap_paths_in_text(content, source_home, target_home)
                        dst.write_text(content, encoding="utf-8")
                    except Exception:
                        shutil.copy2(pf, dst)
                _log("  ✓ Proje yapılandırmaları yüklendi.")

            # F) projects.json
            temp_pjson = temp_extract / "projects.json"
            target_pjson = get_projects_json()
            if temp_pjson.exists():
                try:
                    p_content = temp_pjson.read_text(encoding="utf-8", errors="ignore")
                    if remap_paths and source_home and source_home != target_home:
                        p_content = remap_paths_in_text(p_content, source_home, target_home)
                    if mode == "replace" or not target_pjson.exists():
                        target_pjson.parent.mkdir(parents=True, exist_ok=True)
                        target_pjson.write_text(p_content, encoding="utf-8")
                    elif mode == "merge":
                        _merge_projects_json(temp_pjson, target_pjson, source_home, target_home if remap_paths else None)
                    _log("  ✓ projects.json başarıyla güncellendi.")
                except Exception as e:
                    _log(f"  ⚠️ projects.json aktarılırken uyarı: {e}")

            # G) app_storage_partial.json
            temp_appst = temp_extract / "app_storage_partial.json"
            target_appst = get_app_storage_json()
            if temp_appst.exists() and target_appst.exists():
                try:
                    with open(temp_appst, "r", encoding="utf-8") as asf:
                        partial = json.load(asf)
                    with open(target_appst, "r", encoding="utf-8") as asf:
                        full_st = json.load(asf)
                    for k, v in partial.items():
                        if remap_paths and source_home and source_home != target_home:
                            if isinstance(v, str):
                                v = remap_paths_in_text(v, source_home, target_home)
                        full_st[k] = v
                    with open(target_appst, "w", encoding="utf-8") as asf:
                        json.dump(full_st, asf, indent=2)
                    _log("  ✓ Arayüz görünümü ve sekme düzeni aktarıldı.")
                except Exception:
                    pass

        _log(f"🎉 Antigravity içe aktarma başarıyla tamamlandı! (Mod: {mode.upper()})")
        return True, "Antigravity sohbet ve projeleri başarıyla içe aktarıldı."
    except (zipfile.BadZipFile, zlib.error, EOFError) as e:
        err = f"Bozuk veya geçersiz ZIP dosyası (zip corrupted): {str(e)}"
        _log(f"❌ {err}")
        return False, err
    except Exception as e:
        err = f"İçe aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


def _remap_antigravity_sqlite(db_path: Path, source_home: str, target_home: str):
    """conversation_summaries.db içindeki yolları günceller."""
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        s_norm = source_home.replace("\\", "/")
        t_norm = target_home.replace("\\", "/")
        cur.execute("SELECT id, project_path_encoded, project_root_path_encoded FROM conversation_summaries")
        rows = cur.fetchall()
        for r_id, ppe, prpe in rows:
            new_ppe = ppe
            new_prpe = prpe
            if ppe:
                new_ppe = remap_paths_in_text(ppe, source_home, target_home)
            if prpe:
                new_prpe = remap_paths_in_text(prpe, source_home, target_home)
            if new_ppe != ppe or new_prpe != prpe:
                cur.execute("UPDATE conversation_summaries SET project_path_encoded=?, project_root_path_encoded=? WHERE id=?", (new_ppe, new_prpe, r_id))
        conn.commit()
        conn.close()
    except Exception:
        pass


def _merge_antigravity_summaries(source_db: Path, target_db: Path, source_home: str, target_home: Optional[str], log: Optional[Callable[[str], None]]):
    """İki veritabanını birleştirir."""
    try:
        t_conn = sqlite3.connect(str(target_db))
        t_cur = t_conn.cursor()
        t_cur.execute("SELECT id FROM conversation_summaries")
        existing_ids = {r[0] for r in t_cur.fetchall()}

        s_conn = sqlite3.connect(str(source_db))
        s_cur = s_conn.cursor()
        s_cur.execute("SELECT * FROM conversation_summaries")
        cols = [description[0] for description in s_cur.description]
        rows = s_cur.fetchall()

        inserted = 0
        for r in rows:
            r_dict = dict(zip(cols, r))
            c_id = r_dict["id"]
            if c_id not in existing_ids:
                if target_home and source_home and source_home != target_home:
                    for k in ["project_path_encoded", "project_root_path_encoded", "title"]:
                        if r_dict.get(k):
                            r_dict[k] = remap_paths_in_text(str(r_dict[k]), source_home, target_home)
                placeholders = ":" + ", :".join(cols)
                t_cur.execute(f"INSERT INTO conversation_summaries ({', '.join(cols)}) VALUES ({placeholders})", r_dict)
                inserted += 1

        t_conn.commit()
        s_conn.close()
        t_conn.close()
        if log:
            log(f"  ✓ {inserted} adet yeni sohbet mevcut veritabanına birleştirildi.")
    except Exception as e:
        if log:
            log(f"  ⚠️ Birleştirme uyarısı: {e}")


def _merge_projects_json(temp_json: Path, target_json: Path, source_home: str, target_home: Optional[str]):
    try:
        with open(temp_json, "r", encoding="utf-8") as f:
            src_data = json.load(f).get("projects", {})
        with open(target_json, "r", encoding="utf-8") as f:
            dst_wrapper = json.load(f)
            dst_data = dst_wrapper.get("projects", {})

        for p_id, p_val in src_data.items():
            if target_home and source_home and source_home != target_home:
                raw_str = json.dumps(p_val)
                raw_str = remap_paths_in_text(raw_str, source_home, target_home)
                p_val = json.loads(raw_str)
            if p_id not in dst_data:
                dst_data[p_id] = p_val

        dst_wrapper["projects"] = dst_data
        with open(target_json, "w", encoding="utf-8") as f:
            json.dump(dst_wrapper, f, indent=2)
    except Exception:
        pass


# ==============================================================================
# 2. CLAUDE CODE SOHBET TAŞIMA (EXPORT / IMPORT)
# ==============================================================================

def export_claude_chats(
    output_zip_path: Path,
    log: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Tuple[bool, str]:
    """Claude Code sohbet oturumlarını, projelerini ve komut geçmişini zip dosyasına paketler."""
    def _log(msg: str):
        if log:
            log(msg)

    if is_claude_running():
        _log("ℹ️ Claude oturumları okunup paketleniyor...")

    _log(f"📦 Claude dışa aktarma başlatılıyor: {output_zip_path.name}")
    output_zip_path.parent.mkdir(parents=True, exist_ok=True)

    stats = get_claude_stats()
    _log(f"  Bulunan Claude oturumu: {stats['convo_count']} (Toplam Boyut: ~{stats['total_chat_size_mb']} MB)")

    try:
        claude_dir = get_claude_dir()
        entries: List[Tuple[Path, str, int]] = []

        p_dir = get_claude_projects_dir()
        if p_dir.exists():
            entries.extend(collect_dir_entries(p_dir, "claude", base_dir=claude_dir))

        h_file = get_claude_history_file()
        if h_file.exists() and h_file.is_file():
            entries.append((h_file, "claude/history.jsonl", h_file.stat().st_size))

        s_file = get_claude_settings_file()
        if s_file.exists() and s_file.is_file():
            entries.append((s_file, "claude/settings.json", s_file.stat().st_size))

        def _write_archive(zf: zipfile.ZipFile):
            write_entries_to_zip(zf, entries, progress_callback=progress_callback, log=log)
            manifest = {
                "version": "1.0",
                "export_type": "claude_chats",
                "created_at": datetime.now().isoformat(),
                "source_user_home": str(get_user_home()),
                "source_username": get_user_home().name,
                "convo_count": stats["convo_count"],
                "project_count": stats["project_count"]
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        atomic_zip_write(output_zip_path, _write_archive)

        _log(f"✅ Claude sohbetleri başarıyla dışa aktarıldı: {output_zip_path.name}")
        return True, "Claude sohbetleri başarıyla dışa aktarıldı."
    except Exception as e:
        err = f"Claude dışa aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


def import_claude_chats(
    input_zip_path: Path,
    mode: str = "replace",
    remap_paths: bool = True,
    log: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Tuple[bool, str]:
    """Claude Code yedek paketini sisteme yükler ve yol uyarlamalarını (path remapping) uygular."""
    def _log(msg: str):
        if log:
            log(msg)

    if not input_zip_path.exists():
        return False, f"Yedek bulunamadı: {input_zip_path}"

    _log(f"📥 Claude içe aktarma başlatılıyor: {input_zip_path.name} (Mod: {mode.upper()})")

    try:
        with tempfile.TemporaryDirectory(prefix="agm_cl_imp_") as temp_dir_str:
            temp_extract = Path(temp_dir_str)

            _log("  🔍 ZIP arşivi doğrulanıyor ve açılıyor...")
            extract_zip_with_progress(input_zip_path, temp_extract, progress_callback=progress_callback)

            manifest = {}
            manifest_path = temp_extract / "manifest.json"
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    _log(f"  Kaynak sistem: {manifest.get('source_username', 'Bilinmeyen')} ({manifest.get('source_user_home', '')})")
                except Exception:
                    pass

            source_home = manifest.get("source_user_home", "")
            target_home = str(get_user_home())

            if remap_paths and source_home and source_home != target_home:
                _log(f"  🔄 Claude yol uyarlama aktif: {source_home} ➔ {target_home}")

            if is_claude_running():
                _log("⚠️ Claude açık tespit edildi, kapatılıyor...")
                close_claude_processes()

            if mode == "replace":
                _log("  🧹 Temiz kurulum: Mevcut Claude sohbetleri sıfırlanıyor...")
                clean_claude_conversations(take_backup=True, force_close=True, log=log)

            target_projects_dir = get_claude_projects_dir()
            target_projects_dir.mkdir(parents=True, exist_ok=True)

            src_p_dir = temp_extract / "claude" / "projects"
            if src_p_dir.exists():
                p_count = 0
                for proj_folder in src_p_dir.iterdir():
                    if proj_folder.is_dir():
                        new_name = proj_folder.name
                        if remap_paths and source_home and source_home != target_home:
                            new_name = _remap_claude_folder_name(proj_folder.name, source_home, target_home)

                        dest_proj = target_projects_dir / new_name
                        dest_proj.mkdir(parents=True, exist_ok=True)

                        for root, _, files in os.walk(fs_path(proj_folder)):
                            for f in files:
                                s_fp = Path(root) / f
                                rel = s_fp.relative_to(proj_folder)
                                d_fp = dest_proj / rel
                                os.makedirs(fs_path(d_fp.parent), exist_ok=True)

                                if remap_paths and s_fp.suffix in [".json", ".jsonl", ".txt", ".md"]:
                                    try:
                                        raw = Path(fs_path(s_fp)).read_text(encoding="utf-8", errors="ignore")
                                        remapped = remap_paths_in_text(raw, source_home, target_home)
                                        Path(fs_path(d_fp)).write_text(remapped, encoding="utf-8")
                                    except Exception:
                                        shutil.copy2(fs_path(s_fp), fs_path(d_fp))
                                else:
                                    shutil.copy2(fs_path(s_fp), fs_path(d_fp))
                        p_count += 1
                _log(f"  ✓ {p_count} adet Claude proje oturum dizini başarıyla aktarıldı.")

            src_hist = temp_extract / "claude" / "history.jsonl"
            tgt_hist = get_claude_history_file()
            if src_hist.exists():
                try:
                    h_content = src_hist.read_text(encoding="utf-8", errors="ignore")
                    if remap_paths and source_home and source_home != target_home:
                        h_content = remap_paths_in_text(h_content, source_home, target_home)

                    if mode == "replace" or not tgt_hist.exists():
                        tgt_hist.parent.mkdir(parents=True, exist_ok=True)
                        tgt_hist.write_text(h_content, encoding="utf-8")
                    elif mode == "merge":
                        with open(tgt_hist, "a", encoding="utf-8") as f:
                            f.write("\n" + h_content)
                    _log("  ✓ Claude terminal komut geçmişi aktarıldı.")
                except Exception as e:
                    _log(f"  ⚠️ Claude history aktarılırken uyarı: {e}")

        _log(f"🎉 Claude içe aktarma başarıyla tamamlandı! (Mod: {mode.upper()})")
        return True, "Claude sohbet ve oturumları başarıyla içe aktarıldı."
    except (zipfile.BadZipFile, zlib.error, EOFError) as e:
        err = f"Bozuk veya geçersiz ZIP dosyası (zip corrupted): {str(e)}"
        _log(f"❌ {err}")
        return False, err
    except Exception as e:
        err = f"Claude içe aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


# ==============================================================================
# 3. OPENAI CODEX SOHBET TAŞIMA (EXPORT / IMPORT)
# ==============================================================================

def export_codex_chats(
    output_zip_path: Path,
    log: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Tuple[bool, str]:
    """OpenAI Codex oturumlarını ve geçmişini zip dosyasına paketler."""
    def _log(msg: str):
        if log:
            log(msg)

    if is_codex_running():
        _log("ℹ️ Codex oturumları okunup paketleniyor...")

    _log(f"📦 Codex dışa aktarma başlatılıyor: {output_zip_path.name}")
    output_zip_path.parent.mkdir(parents=True, exist_ok=True)

    stats = get_codex_stats()
    _log(f"  Bulunan Codex oturumu: {stats['convo_count']} (Boyut: ~{stats['total_chat_size_mb']} MB)")

    try:
        codex_dir = get_codex_dir()
        entries: List[Tuple[Path, str, int]] = []

        s_dir = get_codex_sessions_dir()
        if s_dir.exists():
            entries.extend(collect_dir_entries(s_dir, "codex", base_dir=codex_dir))

        h_dir = get_codex_history_dir()
        if h_dir.exists():
            entries.extend(collect_dir_entries(h_dir, "codex", base_dir=codex_dir))

        def _write_archive(zf: zipfile.ZipFile):
            write_entries_to_zip(zf, entries, progress_callback=progress_callback, log=log)
            manifest = {
                "version": "1.0",
                "export_type": "codex_chats",
                "created_at": datetime.now().isoformat(),
                "source_user_home": str(get_user_home()),
                "source_username": get_user_home().name,
                "convo_count": stats["convo_count"]
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        atomic_zip_write(output_zip_path, _write_archive)

        _log(f"✅ Codex oturumları başarıyla dışa aktarıldı: {output_zip_path.name}")
        return True, "Codex oturumları başarıyla dışa aktarıldı."
    except Exception as e:
        err = f"Codex dışa aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


def import_codex_chats(
    input_zip_path: Path,
    mode: str = "replace",
    remap_paths: bool = True,
    log: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Tuple[bool, str]:
    """OpenAI Codex yedek paketini sisteme yükler."""
    def _log(msg: str):
        if log:
            log(msg)

    if not input_zip_path.exists():
        return False, f"Yedek bulunamadı: {input_zip_path}"

    _log(f"📥 Codex içe aktarma başlatılıyor: {input_zip_path.name} (Mod: {mode.upper()})")

    try:
        with tempfile.TemporaryDirectory(prefix="agm_cdx_imp_") as temp_dir_str:
            temp_extract = Path(temp_dir_str)

            _log("  🔍 ZIP arşivi doğrulanıyor ve açılıyor...")
            extract_zip_with_progress(input_zip_path, temp_extract, progress_callback=progress_callback)

            manifest = {}
            manifest_path = temp_extract / "manifest.json"
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    _log(f"  Kaynak sistem: {manifest.get('source_username', 'Bilinmeyen')} ({manifest.get('source_user_home', '')})")
                except Exception:
                    pass

            source_home = manifest.get("source_user_home", "")
            target_home = str(get_user_home())

            if remap_paths and source_home and source_home != target_home:
                _log(f"  🔄 Codex yol uyarlama aktif: {source_home} ➔ {target_home}")

            if is_codex_running():
                _log("⚠️ Codex açık tespit edildi, kapatılıyor...")
                close_codex_processes()

            if mode == "replace":
                _log("  🧹 Temiz kurulum: Mevcut Codex oturumları sıfırlanıyor...")
                clean_codex_conversations(take_backup=True, force_close=True, log=log)

            target_sessions = get_codex_sessions_dir()
            target_history = get_codex_history_dir()
            target_sessions.mkdir(parents=True, exist_ok=True)
            target_history.mkdir(parents=True, exist_ok=True)

            src_s_dir = temp_extract / "codex" / "sessions"
            if src_s_dir.exists():
                s_count = 0
                for root, _, files in os.walk(fs_path(src_s_dir)):
                    for f in files:
                        s_fp = Path(root) / f
                        rel = s_fp.relative_to(src_s_dir)
                        d_fp = target_sessions / rel
                        os.makedirs(fs_path(d_fp.parent), exist_ok=True)

                        if remap_paths and s_fp.suffix in [".json", ".jsonl", ".txt"]:
                            try:
                                raw = Path(fs_path(s_fp)).read_text(encoding="utf-8", errors="ignore")
                                remapped = remap_paths_in_text(raw, source_home, target_home)
                                Path(fs_path(d_fp)).write_text(remapped, encoding="utf-8")
                            except Exception:
                                shutil.copy2(fs_path(s_fp), fs_path(d_fp))
                        else:
                            shutil.copy2(fs_path(s_fp), fs_path(d_fp))
                        s_count += 1
                _log(f"  ✓ {s_count} adet Codex oturum dosyası aktarıldı.")

            src_h_dir = temp_extract / "codex" / "history"
            if src_h_dir.exists():
                for root, _, files in os.walk(fs_path(src_h_dir)):
                    for f in files:
                        s_fp = Path(root) / f
                        rel = s_fp.relative_to(src_h_dir)
                        d_fp = target_history / rel
                        os.makedirs(fs_path(d_fp.parent), exist_ok=True)
                        shutil.copy2(fs_path(s_fp), fs_path(d_fp))
                _log("  ✓ Codex komut geçmişi aktarıldı.")

        _log(f"🎉 Codex içe aktarma başarıyla tamamlandı! (Mod: {mode.upper()})")
        return True, "Codex oturumları başarıyla içe aktarıldı."
    except (zipfile.BadZipFile, zlib.error, EOFError) as e:
        err = f"Bozuk veya geçersiz ZIP dosyası (zip corrupted): {str(e)}"
        _log(f"❌ {err}")
        return False, err
    except Exception as e:
        err = f"Codex içe aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


# ==============================================================================
# 4. TÜM ARAÇLARI BİRLİKTE TAŞIMA (ALL-IN-ONE)
# ==============================================================================

def _scaled_progress(
    cb: Optional[Callable[[int, int], None]],
    offset: int,
    span: int,
    total: int,
) -> Optional[Callable[[int, int], None]]:
    if not cb:
        return None
    def _inner(done: int, sub_total: int):
        ratio = min(1.0, done / max(sub_total, 1))
        cb(offset + int(span * ratio), total)
    return _inner


def export_all_agents_chats(
    output_zip_path: Path,
    log: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Tuple[bool, str]:
    """Antigravity, Claude ve Codex sohbetlerini tek bir dev pakette toplar."""
    def _log(msg: str):
        if log:
            log(msg)

    _log("📦 TÜM ARAÇLAR İÇİN ORTAK SOHBET DIŞA AKTARIMI BAŞLATILIYOR...")

    s_agy = max(int(get_system_stats().get("total_chat_size_mb", 0) * 1024 * 1024), 1024)
    s_cl = max(int(get_claude_stats().get("total_chat_size_mb", 0) * 1024 * 1024), 1024)
    s_cdx = max(int(get_codex_stats().get("total_chat_size_mb", 0) * 1024 * 1024), 1024)
    total_weight = s_agy + s_cl + s_cdx

    try:
        with tempfile.TemporaryDirectory(prefix="agm_all_exp_") as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            f1 = temp_dir / "antigravity.zip"
            f2 = temp_dir / "claude.zip"
            f3 = temp_dir / "codex.zip"

            ok1, err1 = export_chats_and_projects(f1, log=log, progress_callback=_scaled_progress(progress_callback, 0, s_agy, total_weight))
            if not ok1:
                return False, err1

            ok2, err2 = export_claude_chats(f2, log=log, progress_callback=_scaled_progress(progress_callback, s_agy, s_cl, total_weight))
            if not ok2:
                return False, err2

            ok3, err3 = export_codex_chats(f3, log=log, progress_callback=_scaled_progress(progress_callback, s_agy + s_cl, s_cdx, total_weight))
            if not ok3:
                return False, err3

            pkg_entries: List[Tuple[Path, str, int]] = []
            for fp, arc in [(f1, "packages/antigravity.zip"), (f2, "packages/claude.zip"), (f3, "packages/codex.zip")]:
                if fp.exists():
                    pkg_entries.append((fp, arc, fp.stat().st_size))

            def _write_outer(zf: zipfile.ZipFile):
                write_entries_to_zip(zf, pkg_entries, log=log)
                manifest = {
                    "version": "1.0",
                    "export_type": "all_agents_chats",
                    "created_at": datetime.now().isoformat(),
                    "source_user_home": str(get_user_home()),
                    "source_username": get_user_home().name,
                    "included": ["antigravity", "claude", "codex"]
                }
                zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            atomic_zip_write(output_zip_path, _write_outer)

            if progress_callback:
                progress_callback(total_weight, total_weight)

        _log(f"🎉 Tüm araçların sohbetleri tek pakette toplandı: {output_zip_path.name}")
        return True, "Tüm araçların sohbetleri başarıyla dışa aktarıldı."
    except Exception as e:
        err = f"Toplu dışa aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


def import_all_agents_chats(
    input_zip_path: Path,
    mode: str = "replace",
    remap_paths: bool = True,
    log: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Tuple[bool, str]:
    """Tüm araçları içeren ortak yedek paketini içe aktarır."""
    def _log(msg: str):
        if log:
            log(msg)

    if not input_zip_path.exists():
        return False, f"Yedek bulunamadı: {input_zip_path}"

    _log(f"📥 TÜM ARAÇLARIN ORTAK YEDEĞİ İÇE AKTARILIYOR: {input_zip_path.name}")

    try:
        with tempfile.TemporaryDirectory(prefix="agm_all_imp_") as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            extract_zip_with_progress(
                input_zip_path,
                temp_dir,
                progress_callback=_scaled_progress(progress_callback, 0, 20, 100),
            )

            p_ant = temp_dir / "packages" / "antigravity.zip"
            p_claude = temp_dir / "packages" / "claude.zip"
            p_codex = temp_dir / "packages" / "codex.zip"

            sub_jobs = [
                (p_ant, import_chats_and_projects),
                (p_claude, import_claude_chats),
                (p_codex, import_codex_chats),
            ]
            existing = [(p, fn, max(p.stat().st_size, 1)) for p, fn in sub_jobs if p.exists()]
            total_sz = sum(sz for _, _, sz in existing) or 1
            offset = 20

            for p, fn, sz in existing:
                span = max(1, int(80 * sz / total_sz))
                ok, err = fn(
                    p,
                    mode=mode,
                    remap_paths=remap_paths,
                    log=log,
                    progress_callback=_scaled_progress(progress_callback, offset, span, 100),
                )
                if not ok:
                    return False, err
                offset += span

            if progress_callback:
                progress_callback(100, 100)

        _log("🎉 Tüm araçların yedekleri başarıyla içe aktarıldı!")
        return True, "Tüm araçların yedekleri başarıyla kuruldu."
    except (zipfile.BadZipFile, zlib.error, EOFError) as e:
        err = f"Bozuk veya geçersiz ZIP dosyası (zip corrupted): {str(e)}"
        _log(f"❌ {err}")
        return False, err
    except Exception as e:
        err = f"Toplu içe aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err
