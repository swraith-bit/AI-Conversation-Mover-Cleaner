"""
chat_migrator.py - Antigravity, Claude Code ve OpenAI Codex sohbet/oturum taşıma (Export/Import) motoru.
Farklı bilgisayarlardaki kullanıcı yollarını (Path Remapping) otomatik uyarlar.
"""

import os
import re
import json
import shutil
import sqlite3
import zipfile
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Callable, Optional, Tuple, List

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
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            sum_db = get_summaries_db()
            if sum_db.exists():
                zf.write(sum_db, arcname="antigravity/conversation_summaries.db")

            proto = get_proto_summaries()
            if proto.exists():
                zf.write(proto, arcname="antigravity/agyhub_summaries_proto.pb")

            convos_dir = get_conversations_dir()
            if convos_dir.exists():
                for f in convos_dir.glob("*"):
                    if f.is_file():
                        zf.write(f, arcname=f"antigravity/conversations/{f.name}")

            brain_dir = get_brain_dir()
            if brain_dir.exists():
                file_list = []
                for root, _, fs in os.walk(brain_dir):
                    for fn in fs:
                        file_list.append(Path(root) / fn)
                total_files = len(file_list)
                for idx, full_p in enumerate(file_list):
                    rel_p = full_p.relative_to(brain_dir)
                    zf.write(full_p, arcname=f"antigravity/brain/{rel_p.as_posix()}")
                    if progress_callback and idx % 50 == 0:
                        progress_callback(idx, total_files)

            prj_dir = get_config_projects_dir()
            if prj_dir.exists():
                for f in prj_dir.glob("*.json"):
                    zf.write(f, arcname=f"config/projects/{f.name}")

            p_json = get_projects_json()
            if p_json.exists():
                zf.write(p_json, arcname="projects.json")

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
    log: Optional[Callable[[str], None]] = None
) -> Tuple[bool, str]:
    """Antigravity yedek paketini sisteme yükler."""
    def _log(msg: str):
        if log:
            log(msg)

    if not input_zip_path.exists():
        return False, f"Yedek dosyası bulunamadı: {input_zip_path}"

    if is_antigravity_running():
        _log("⚠️ Antigravity açık tespit edildi, kapatılıyor...")
        close_antigravity_processes()

    _log(f"📥 Antigravity içe aktarma başlatılıyor: {input_zip_path.name} (Mod: {mode.upper()})")

    try:
        with zipfile.ZipFile(input_zip_path, "r") as zf:
            manifest = {}
            if "manifest.json" in zf.namelist():
                try:
                    manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
                    _log(f"  Kaynak sistem: {manifest.get('source_username', 'Bilinmeyen')} ({manifest.get('source_user_home', '')})")
                except Exception:
                    pass

            source_home = manifest.get("source_user_home", "")
            target_home = str(get_user_home())

            if remap_paths and source_home and source_home != target_home:
                _log(f"  🔄 Yol uyarlama aktif: {source_home} ➔ {target_home}")

            if mode == "replace":
                _log("  🧹 Temiz kurulum: Mevcut veriler sıfırlanıyor...")
                clean_all_conversations_and_projects(take_backup=True, force_close=True, log=log)

            temp_extract = input_zip_path.parent / "_temp_antigravity_import"
            if temp_extract.exists():
                shutil.rmtree(temp_extract, ignore_errors=True)
            temp_extract.mkdir(parents=True, exist_ok=True)

            try:
                zf.extractall(temp_extract)

                # A) conversations/
                temp_convos = temp_extract / "antigravity" / "conversations"
                target_convos = get_conversations_dir()
                target_convos.mkdir(parents=True, exist_ok=True)
                if temp_convos.exists():
                    convo_count = 0
                    for cf in temp_convos.glob("*"):
                        if cf.is_file():
                            dst = target_convos / cf.name
                            shutil.copy2(cf, dst)
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
                                shutil.rmtree(dst_dir, ignore_errors=True)
                            shutil.copytree(sub, dst_dir)
                            brain_dirs_count += 1

                            if remap_paths and source_home and source_home != target_home:
                                for root, _, files in os.walk(dst_dir):
                                    for fn in files:
                                        if fn.endswith((".json", ".jsonl", ".txt", ".md", ".log")):
                                            fp = Path(root) / fn
                                            try:
                                                raw = fp.read_text(encoding="utf-8", errors="ignore")
                                                remapped = remap_paths_in_text(raw, source_home, target_home)
                                                if raw != remapped:
                                                    fp.write_text(remapped, encoding="utf-8")
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

            finally:
                shutil.rmtree(temp_extract, ignore_errors=True)

        _log(f"🎉 Antigravity içe aktarma başarıyla tamamlandı! (Mod: {mode.upper()})")
        return True, "Antigravity sohbet ve projeleri başarıyla içe aktarıldı."
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
    log: Optional[Callable[[str], None]] = None
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
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            p_dir = get_claude_projects_dir()
            if p_dir.exists():
                for root, _, files in os.walk(p_dir):
                    for f in files:
                        fp = Path(root) / f
                        rel = fp.relative_to(claude_dir)
                        zf.write(fp, arcname=f"claude/{rel.as_posix()}")

            h_file = get_claude_history_file()
            if h_file.exists():
                zf.write(h_file, arcname="claude/history.jsonl")

            s_file = get_claude_settings_file()
            if s_file.exists():
                zf.write(s_file, arcname="claude/settings.json")

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
    log: Optional[Callable[[str], None]] = None
) -> Tuple[bool, str]:
    """Claude Code yedek paketini sisteme yükler ve yol uyarlamalarını (path remapping) uygular."""
    def _log(msg: str):
        if log:
            log(msg)

    if not input_zip_path.exists():
        return False, f"Yedek bulunamadı: {input_zip_path}"

    if is_claude_running():
        _log("⚠️ Claude açık tespit edildi, kapatılıyor...")
        close_claude_processes()

    _log(f"📥 Claude içe aktarma başlatılıyor: {input_zip_path.name} (Mod: {mode.upper()})")

    try:
        with zipfile.ZipFile(input_zip_path, "r") as zf:
            manifest = {}
            if "manifest.json" in zf.namelist():
                try:
                    manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
                    _log(f"  Kaynak sistem: {manifest.get('source_username', 'Bilinmeyen')} ({manifest.get('source_user_home', '')})")
                except Exception:
                    pass

            source_home = manifest.get("source_user_home", "")
            target_home = str(get_user_home())

            if remap_paths and source_home and source_home != target_home:
                _log(f"  🔄 Claude yol uyarlama aktif: {source_home} ➔ {target_home}")

            if mode == "replace":
                _log("  🧹 Temiz kurulum: Mevcut Claude sohbetleri sıfırlanıyor...")
                clean_claude_conversations(take_backup=True, force_close=True, log=log)

            target_claude_dir = get_claude_dir()
            target_projects_dir = get_claude_projects_dir()
            target_projects_dir.mkdir(parents=True, exist_ok=True)

            temp_extract = input_zip_path.parent / "_temp_claude_import"
            if temp_extract.exists():
                shutil.rmtree(temp_extract, ignore_errors=True)
            temp_extract.mkdir(parents=True, exist_ok=True)

            try:
                zf.extractall(temp_extract)

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

                            for root, _, files in os.walk(proj_folder):
                                for f in files:
                                    s_fp = Path(root) / f
                                    rel = s_fp.relative_to(proj_folder)
                                    d_fp = dest_proj / rel
                                    d_fp.parent.mkdir(parents=True, exist_ok=True)

                                    if remap_paths and s_fp.suffix in [".json", ".jsonl", ".txt", ".md"]:
                                        try:
                                            raw = s_fp.read_text(encoding="utf-8", errors="ignore")
                                            remapped = remap_paths_in_text(raw, source_home, target_home)
                                            d_fp.write_text(remapped, encoding="utf-8")
                                        except Exception:
                                            shutil.copy2(s_fp, d_fp)
                                    else:
                                        shutil.copy2(s_fp, d_fp)
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

            finally:
                shutil.rmtree(temp_extract, ignore_errors=True)

        _log(f"🎉 Claude içe aktarma başarıyla tamamlandı! (Mod: {mode.upper()})")
        return True, "Claude sohbet ve oturumları başarıyla içe aktarıldı."
    except Exception as e:
        err = f"Claude içe aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


# ==============================================================================
# 3. OPENAI CODEX SOHBET TAŞIMA (EXPORT / IMPORT)
# ==============================================================================

def export_codex_chats(
    output_zip_path: Path,
    log: Optional[Callable[[str], None]] = None
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
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            s_dir = get_codex_sessions_dir()
            if s_dir.exists():
                for root, _, files in os.walk(s_dir):
                    for f in files:
                        fp = Path(root) / f
                        rel = fp.relative_to(codex_dir)
                        zf.write(fp, arcname=f"codex/{rel.as_posix()}")

            h_dir = get_codex_history_dir()
            if h_dir.exists():
                for root, _, files in os.walk(h_dir):
                    for f in files:
                        fp = Path(root) / f
                        rel = fp.relative_to(codex_dir)
                        zf.write(fp, arcname=f"codex/{rel.as_posix()}")

            manifest = {
                "version": "1.0",
                "export_type": "codex_chats",
                "created_at": datetime.now().isoformat(),
                "source_user_home": str(get_user_home()),
                "source_username": get_user_home().name,
                "convo_count": stats["convo_count"]
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

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
    log: Optional[Callable[[str], None]] = None
) -> Tuple[bool, str]:
    """OpenAI Codex yedek paketini sisteme yükler."""
    def _log(msg: str):
        if log:
            log(msg)

    if not input_zip_path.exists():
        return False, f"Yedek bulunamadı: {input_zip_path}"

    if is_codex_running():
        _log("⚠️ Codex açık tespit edildi, kapatılıyor...")
        close_codex_processes()

    _log(f"📥 Codex içe aktarma başlatılıyor: {input_zip_path.name} (Mod: {mode.upper()})")

    try:
        with zipfile.ZipFile(input_zip_path, "r") as zf:
            manifest = {}
            if "manifest.json" in zf.namelist():
                try:
                    manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
                    _log(f"  Kaynak sistem: {manifest.get('source_username', 'Bilinmeyen')} ({manifest.get('source_user_home', '')})")
                except Exception:
                    pass

            source_home = manifest.get("source_user_home", "")
            target_home = str(get_user_home())

            if remap_paths and source_home and source_home != target_home:
                _log(f"  🔄 Codex yol uyarlama aktif: {source_home} ➔ {target_home}")

            if mode == "replace":
                _log("  🧹 Temiz kurulum: Mevcut Codex oturumları sıfırlanıyor...")
                clean_codex_conversations(take_backup=True, force_close=True, log=log)

            codex_dir = get_codex_dir()
            target_sessions = get_codex_sessions_dir()
            target_history = get_codex_history_dir()
            target_sessions.mkdir(parents=True, exist_ok=True)
            target_history.mkdir(parents=True, exist_ok=True)

            temp_extract = input_zip_path.parent / "_temp_codex_import"
            if temp_extract.exists():
                shutil.rmtree(temp_extract, ignore_errors=True)
            temp_extract.mkdir(parents=True, exist_ok=True)

            try:
                zf.extractall(temp_extract)

                src_s_dir = temp_extract / "codex" / "sessions"
                if src_s_dir.exists():
                    s_count = 0
                    for root, _, files in os.walk(src_s_dir):
                        for f in files:
                            s_fp = Path(root) / f
                            rel = s_fp.relative_to(src_s_dir)
                            d_fp = target_sessions / rel
                            d_fp.parent.mkdir(parents=True, exist_ok=True)

                            if remap_paths and s_fp.suffix in [".json", ".jsonl", ".txt"]:
                                try:
                                    raw = s_fp.read_text(encoding="utf-8", errors="ignore")
                                    remapped = remap_paths_in_text(raw, source_home, target_home)
                                    d_fp.write_text(remapped, encoding="utf-8")
                                except Exception:
                                    shutil.copy2(s_fp, d_fp)
                            else:
                                shutil.copy2(s_fp, d_fp)
                            s_count += 1
                    _log(f"  ✓ {s_count} adet Codex oturum dosyası aktarıldı.")

                src_h_dir = temp_extract / "codex" / "history"
                if src_h_dir.exists():
                    for root, _, files in os.walk(src_h_dir):
                        for f in files:
                            s_fp = Path(root) / f
                            rel = s_fp.relative_to(src_h_dir)
                            d_fp = target_history / rel
                            d_fp.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(s_fp, d_fp)
                    _log("  ✓ Codex komut geçmişi aktarıldı.")

            finally:
                shutil.rmtree(temp_extract, ignore_errors=True)

        _log(f"🎉 Codex içe aktarma başarıyla tamamlandı! (Mod: {mode.upper()})")
        return True, "Codex oturumları başarıyla içe aktarıldı."
    except Exception as e:
        err = f"Codex içe aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


# ==============================================================================
# 4. TÜM ARAÇLARI BİRLİKTE TAŞIMA (ALL-IN-ONE)
# ==============================================================================

def export_all_agents_chats(
    output_zip_path: Path,
    log: Optional[Callable[[str], None]] = None
) -> Tuple[bool, str]:
    """Antigravity, Claude ve Codex sohbetlerini tek bir dev pakette toplar."""
    def _log(msg: str):
        if log:
            log(msg)

    _log("📦 TÜM ARAÇLAR İÇİN ORTAK SOHBET DIŞA AKTARIMI BAŞLATILIYOR...")

    temp_dir = output_zip_path.parent / "_temp_all_export"
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        f1 = temp_dir / "antigravity.zip"
        f2 = temp_dir / "claude.zip"
        f3 = temp_dir / "codex.zip"

        export_chats_and_projects(f1, log=log)
        export_claude_chats(f2, log=log)
        export_codex_chats(f3, log=log)

        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if f1.exists():
                zf.write(f1, arcname="packages/antigravity.zip")
            if f2.exists():
                zf.write(f2, arcname="packages/claude.zip")
            if f3.exists():
                zf.write(f3, arcname="packages/codex.zip")

            manifest = {
                "version": "1.0",
                "export_type": "all_agents_chats",
                "created_at": datetime.now().isoformat(),
                "source_user_home": str(get_user_home()),
                "source_username": get_user_home().name,
                "included": ["antigravity", "claude", "codex"]
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        _log(f"🎉 Tüm araçların sohbetleri tek pakette toplandı: {output_zip_path.name}")
        return True, "Tüm araçların sohbetleri başarıyla dışa aktarıldı."
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def import_all_agents_chats(
    input_zip_path: Path,
    mode: str = "replace",
    remap_paths: bool = True,
    log: Optional[Callable[[str], None]] = None
) -> Tuple[bool, str]:
    """Tüm araçları içeren ortak yedek paketini içe aktarır."""
    def _log(msg: str):
        if log:
            log(msg)

    _log(f"📥 TÜM ARAÇLARIN ORTAK YEDEĞİ İÇE AKTARILIYOR: {input_zip_path.name}")

    temp_dir = input_zip_path.parent / "_temp_all_import"
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(input_zip_path, "r") as zf:
            zf.extractall(temp_dir)

        p_ant = temp_dir / "packages" / "antigravity.zip"
        p_claude = temp_dir / "packages" / "claude.zip"
        p_codex = temp_dir / "packages" / "codex.zip"

        if p_ant.exists():
            import_chats_and_projects(p_ant, mode=mode, remap_paths=remap_paths, log=log)
        if p_claude.exists():
            import_claude_chats(p_claude, mode=mode, remap_paths=remap_paths, log=log)
        if p_codex.exists():
            import_codex_chats(p_codex, mode=mode, remap_paths=remap_paths, log=log)

        _log("🎉 Tüm araçların yedekleri başarıyla içe aktarıldı!")
        return True, "Tüm araçların yedekleri başarıyla kuruldu."
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
