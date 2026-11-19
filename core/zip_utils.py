"""
zip_utils.py - Fast, atomic, Windows-safe ZIP export/import helpers with byte-level progress.
"""

import os
import time
import shutil
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Tuple

CHUNK_SIZE = 1024 * 1024  # 1 MB

# Skip deflate on formats that are already compressed; saves huge CPU/time on large brain/media folders.
INCOMPRESSIBLE_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico",
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".mp3", ".wav", ".ogg",
    ".zip", ".gz", ".bz2", ".xz", ".7z", ".rar", ".zst", ".pdf",
    ".woff", ".woff2",
}


def fs_path(p: Path) -> str:
    """Returns a Windows long-path-safe string when path length nears MAX_PATH."""
    s = os.path.abspath(str(p))
    if os.name == "nt" and not s.startswith("\\\\?\\") and len(s) >= 240:
        return "\\\\?\\" + s
    return s


def compression_for(path: Path) -> int:
    """Chooses ZIP_STORED for already-compressed files, ZIP_DEFLATED otherwise."""
    if path.suffix.lower() in INCOMPRESSIBLE_EXTS:
        return zipfile.ZIP_STORED
    return zipfile.ZIP_DEFLATED


def collect_dir_entries(root_dir: Path, arc_prefix: str, base_dir: Optional[Path] = None) -> List[Tuple[Path, str, int]]:
    """Collects (src_path, arcname, size_bytes) tuples under root_dir."""
    entries: List[Tuple[Path, str, int]] = []
    if not root_dir.exists():
        return entries
    rel_base = base_dir or root_dir
    for r, _, files in os.walk(fs_path(root_dir)):
        for fn in files:
            full_p = Path(r) / fn
            try:
                if full_p.is_symlink():
                    continue
                st = os.stat(fs_path(full_p))
                rel = full_p.relative_to(rel_base).as_posix()
                arc = f"{arc_prefix}/{rel}" if arc_prefix else rel
                entries.append((full_p, arc, st.st_size))
            except OSError:
                continue
    return entries


def snapshot_sqlite_db(db_path: Path, temp_dir: Path) -> Path:
    """Creates a lock-safe, WAL-consistent snapshot of a SQLite database."""
    snap_path = temp_dir / db_path.name
    src_conn = None
    dst_conn = None
    try:
        src_conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True, timeout=5.0)
        dst_conn = sqlite3.connect(str(snap_path))
        src_conn.backup(dst_conn)
        return snap_path
    except Exception:
        shutil.copy2(fs_path(db_path), fs_path(snap_path))
        return snap_path
    finally:
        if dst_conn:
            try:
                dst_conn.close()
            except Exception:
                pass
        if src_conn:
            try:
                src_conn.close()
            except Exception:
                pass


def atomic_zip_write(
    output_zip_path: Path,
    write_fn: Callable[[zipfile.ZipFile], None],
) -> None:
    """Writes a zip archive to a temp file and atomically moves it to output_zip_path on success."""
    output_zip_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_zip_path.parent / f".{output_zip_path.name}.{os.getpid()}.tmp"
    try:
        with zipfile.ZipFile(
            fs_path(tmp_path),
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=1,
            allowZip64=True,
        ) as zf:
            write_fn(zf)
        os.replace(fs_path(tmp_path), fs_path(output_zip_path))
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def write_entries_to_zip(
    zf: zipfile.ZipFile,
    entries: Iterable[Tuple[Path, str, int]],
    total_bytes: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    log: Optional[Callable[[str], None]] = None,
) -> int:
    """Writes (src_path, arcname, size) entries into zf with chunked byte progress and lock safety."""
    entry_list = list(entries)
    if total_bytes is None:
        total_bytes = sum(sz for _, _, sz in entry_list)
    done_bytes = 0
    last_emit = 0.0
    written_count = 0

    if progress_callback:
        progress_callback(0, max(total_bytes, 1))

    for src_path, arcname, size_hint in entry_list:
        src_str = fs_path(src_path)
        try:
            src_f = open(src_str, "rb")
        except OSError as e:
            if log:
                log(f"  ⚠️ Atlandı (okunamadı: {arcname}): {e}")
            done_bytes += size_hint
            continue

        try:
            with src_f:
                try:
                    zinfo = zipfile.ZipInfo.from_file(src_str, arcname=arcname)
                except ValueError:
                    zinfo = zipfile.ZipInfo(arcname)
                zinfo.compress_type = compression_for(src_path)
                force_zip64 = size_hint >= zipfile.ZIP64_LIMIT
                with zf.open(zinfo, "w", force_zip64=force_zip64) as dst:
                    while True:
                        chunk = src_f.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        dst.write(chunk)
                        done_bytes += len(chunk)
                        if progress_callback:
                            now = time.monotonic()
                            if now - last_emit >= 0.1:
                                progress_callback(min(done_bytes, max(total_bytes, done_bytes)), max(total_bytes, done_bytes, 1))
                                last_emit = now
                written_count += 1
        except OSError as e:
            if log:
                log(f"  ⚠️ Dosya paketlenemedi ({arcname}): {e}")

    if progress_callback:
        final_total = max(total_bytes, done_bytes, 1)
        progress_callback(final_total, final_total)

    return written_count


def extract_zip_with_progress(
    input_zip_path: Path,
    dest_dir: Path,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    """Validates (via CRC check during streaming read) and extracts a zip into dest_dir safely."""
    dest_root = os.path.abspath(str(dest_dir))
    with zipfile.ZipFile(fs_path(input_zip_path), "r") as zf:
        members = zf.infolist()
        total_bytes = sum(m.file_size for m in members if not m.is_dir())
        done_bytes = 0
        last_emit = 0.0

        if progress_callback:
            progress_callback(0, max(total_bytes, 1))

        for member in members:
            # Prevent ZipSlip path traversal
            rel_parts = [p for p in member.filename.replace("\\", "/").split("/") if p not in ("", ".")]
            if any(p == ".." for p in rel_parts):
                raise zipfile.BadZipFile(f"Unsafe path in archive: {member.filename}")
            if not rel_parts:
                continue

            target_path = Path(dest_root).joinpath(*rel_parts)
            if member.is_dir():
                os.makedirs(fs_path(target_path), exist_ok=True)
                continue

            os.makedirs(fs_path(target_path.parent), exist_ok=True)
            with zf.open(member, "r") as src, open(fs_path(target_path), "wb") as dst:
                while True:
                    chunk = src.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    dst.write(chunk)
                    done_bytes += len(chunk)
                    if progress_callback:
                        now = time.monotonic()
                        if now - last_emit >= 0.1:
                            progress_callback(min(done_bytes, max(total_bytes, done_bytes)), max(total_bytes, done_bytes, 1))
                            last_emit = now

        if progress_callback:
            final_total = max(total_bytes, 1)
            progress_callback(final_total, final_total)
