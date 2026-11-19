"""
cleaner.py - Antigravity, Claude Code ve OpenAI Codex sohbet/oturum temizleme motoru.
Otomatik güvenlik yedeği (Undo koruması) içerir.
"""

import os
import shutil
import sqlite3
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Callable, Optional, Tuple

from core.paths import (
    get_summaries_db,
    get_proto_summaries,
    get_conversations_dir,
    get_brain_dir,
    get_presence_dir,
    get_config_projects_dir,
    get_projects_json,
    get_app_storage_json,
    is_antigravity_running,
    close_antigravity_processes,
    get_claude_dir,
    get_claude_projects_dir,
    get_claude_history_file,
    get_claude_settings_file,
    get_claude_config_file,
    is_claude_running,
    close_claude_processes,
    get_codex_dir,
    get_codex_sessions_dir,
    get_codex_history_dir,
    get_codex_config_file,
    is_codex_running,
    close_codex_processes,
    get_user_home
)


def get_default_backup_dir() -> Path:
    """Yedeklerin saklanacağı varsayılan dizini döndürür."""
    base = Path(__file__).resolve().parent.parent / "backups"
    base.mkdir(parents=True, exist_ok=True)
    return base


# ==============================================================================
# 1. ANTIGRAVITY TEMİZLEME & GERİ YÜKLEME
# ==============================================================================

def create_safety_backup(backup_path: Optional[Path] = None, log: Optional[Callable[[str], None]] = None) -> Path:
    """Sıfırlama öncesinde tüm Antigravity sohbet, proje ve yapılandırmalarını yedekler."""
    def _log(msg: str):
        if log:
            log(msg)

    if backup_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = get_default_backup_dir() / f"antigravity_guvenlik_yedegi_{timestamp}.zip"

    _log(f"🛡️ Antigravity güvenlik yedeği oluşturuluyor: {backup_path.name}")

    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
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
            for root, _, files in os.walk(brain_dir):
                for file in files:
                    full_p = Path(root) / file
                    rel_p = full_p.relative_to(brain_dir)
                    zf.write(full_p, arcname=f"antigravity/brain/{rel_p.as_posix()}")

        prj_dir = get_config_projects_dir()
        if prj_dir.exists():
            for f in prj_dir.glob("*.json"):
                zf.write(f, arcname=f"config/projects/{f.name}")

        p_json = get_projects_json()
        if p_json.exists():
            zf.write(p_json, arcname="projects.json")

        app_st = get_app_storage_json()
        if app_st.exists():
            zf.write(app_st, arcname="app_storage.json")

        manifest = {
            "agent": "antigravity",
            "backup_type": "safety_backup",
            "created_at": datetime.now().isoformat(),
            "source_user_home": str(get_user_home())
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

    _log("✅ Antigravity güvenlik yedeği başarıyla alındı.")
    return backup_path


def restore_backup(zip_path: Path, log: Optional[Callable[[str], None]] = None) -> Tuple[bool, str]:
    """Antigravity güvenlik yedeğini geri yükler (Undo)."""
    def _log(msg: str):
        if log:
            log(msg)

    if not zip_path.exists():
        return False, f"Yedek dosyası bulunamadı: {zip_path}"

    if is_antigravity_running():
        _log("⚠️ Antigravity açık tespit edildi, kapatılıyor...")
        close_antigravity_processes()

    _log(f"📥 Yedekten geri yükleniyor: {zip_path.name}")

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.infolist():
                if member.is_dir() or member.filename == "manifest.json":
                    continue

                target_path = None
                fn = member.filename

                if fn.startswith("antigravity/"):
                    sub = fn[len("antigravity/"):]
                    target_path = get_summaries_db().parent / sub
                elif fn.startswith("config/projects/"):
                    sub = fn[len("config/projects/"):]
                    target_path = get_config_projects_dir() / sub
                elif fn == "projects.json":
                    target_path = get_projects_json()
                elif fn == "app_storage.json":
                    target_path = get_app_storage_json()

                if target_path:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(target_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)

        _log("✅ Antigravity yedeği başarıyla geri yüklendi!")
        return True, "Antigravity yedeği başarıyla geri yüklendi."
    except Exception as e:
        err = f"Geri yükleme sırasında hata: {str(e)}"
        _log(f"❌ {err}")
        return False, err


def clean_all_conversations_and_projects(
    take_backup: bool = True,
    force_close: bool = True,
    log: Optional[Callable[[str], None]] = None
) -> Tuple[bool, str]:
    """Antigravity sohbet ve projelerini tek hamlede sıfırlar."""
    def _log(msg: str):
        if log:
            log(msg)

    if is_antigravity_running():
        if force_close:
            _log("⚠️ Antigravity çalışıyor, kapatılıyor...")
            close_antigravity_processes()
        else:
            return False, "Antigravity açık! Lütfen önce Antigravity'yi kapatın."

    if take_backup:
        try:
            backup_file = create_safety_backup(log=log)
            _log(f"📁 Güvenlik yedeği kaydedildi: {backup_file.name}")
        except Exception as e:
            _log(f"⚠️ Güvenlik yedeği alınırken hata: {e}")

    _log("🧹 Antigravity sohbetleri ve projeleri temizleniyor...")

    sum_db = get_summaries_db()
    if sum_db.exists():
        try:
            conn = sqlite3.connect(str(sum_db))
            cur = conn.cursor()
            tables = [
                "conversation_summaries", "conversations_fts", "conversations_fts_data",
                "conversations_fts_idx", "conversations_fts_content", "conversations_fts_docsize",
                "conversations_fts_config", "conversation_parents"
            ]
            for t in tables:
                try:
                    cur.execute(f"DELETE FROM {t}")
                except Exception:
                    pass
            conn.commit()
            cur.execute("VACUUM")
            conn.close()
            _log("  ✓ conversation_summaries.db veritabanı sıfırlandı.")
        except Exception as e:
            _log(f"  ⚠️ conversation_summaries.db uyarısı: {e}")

        for ext in [".db-wal", ".db-shm"]:
            w = Path(str(sum_db) + ext)
            if w.exists():
                try:
                    w.unlink()
                except Exception:
                    pass

    proto = get_proto_summaries()
    if proto.exists():
        try:
            proto.unlink()
            _log("  ✓ agyhub_summaries_proto.pb silindi.")
        except Exception as e:
            _log(f"  ⚠️ agyhub_summaries_proto.pb uyarısı: {e}")

    convos_dir = get_conversations_dir()
    if convos_dir.exists():
        del_count = 0
        for f in convos_dir.glob("*"):
            if f.is_file():
                try:
                    f.unlink()
                    del_count += 1
                except Exception:
                    pass
        _log(f"  ✓ {del_count} adet sohbet veritabanı (.db) silindi.")

    brain_dir = get_brain_dir()
    if brain_dir.exists():
        del_brain_count = 0
        for sub in brain_dir.iterdir():
            if sub.is_dir():
                try:
                    shutil.rmtree(sub, ignore_errors=True)
                    del_brain_count += 1
                except Exception:
                    pass
        _log(f"  ✓ {del_brain_count} adet sohbet hafıza/log dizini (brain) temizlendi.")

    pres_dir = get_presence_dir()
    if pres_dir.exists():
        for lk in pres_dir.glob("*.lock"):
            try:
                lk.unlink()
            except Exception:
                pass

    prj_dir = get_config_projects_dir()
    if prj_dir.exists():
        del_prj_count = 0
        for pf in prj_dir.glob("*.json"):
            if pf.name == "outside-of-project.json":
                continue
            try:
                with open(pf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "sidecar" not in data:
                        pf.unlink()
                        del_prj_count += 1
            except Exception:
                try:
                    pf.unlink()
                    del_prj_count += 1
                except Exception:
                    pass
        _log(f"  ✓ {del_prj_count} adet kullanıcı proje kaydı silindi.")

    p_json = get_projects_json()
    if p_json.exists():
        try:
            with open(p_json, "w", encoding="utf-8") as f:
                json.dump({"projects": {}}, f, indent=2)
            _log("  ✓ projects.json sıfırlandı.")
        except Exception as e:
            _log(f"  ⚠️ projects.json uyarısı: {e}")

    app_st = get_app_storage_json()
    if app_st.exists():
        try:
            with open(app_st, "r", encoding="utf-8") as f:
                storage_data = json.load(f)

            storage_data["projectsOrder"] = "[]"
            storage_data["aux-pane-v2-session"] = "{}"
            storage_data["aux-pane-session"] = "{}"
            storage_data["comments"] = '{"files":{},"artifacts":{},"diffs":{},"drafts":{}}'

            keys_to_remove = [k for k in storage_data.keys() if k.startswith("antigravity-multi-conversation-layout-v3-")]
            for k in keys_to_remove:
                del storage_data[k]

            with open(app_st, "w", encoding="utf-8") as f:
                json.dump(storage_data, f, indent=2)

            _log("  ✓ app_storage.json arayüz/sekme durumu temizlendi.")
        except Exception as e:
            _log(f"  ⚠️ app_storage.json uyarısı: {e}")

    _log("🎉 Antigravity sohbet ve projeleri başarıyla sıfırlandı.")
    return True, "Antigravity sohbet ve projeleri başarıyla temizlendi."


# ==============================================================================
# 2. CLAUDE CODE & DESKTOP TEMİZLEME & GERİ YÜKLEME
# ==============================================================================

def create_claude_safety_backup(backup_path: Optional[Path] = None, log: Optional[Callable[[str], None]] = None) -> Path:
    """Claude Code sohbet oturumlarını, geçmişini ve ayarlarını yedekler."""
    def _log(msg: str):
        if log:
            log(msg)

    if backup_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = get_default_backup_dir() / f"claude_guvenlik_yedegi_{timestamp}.zip"

    _log(f"🛡️ Claude güvenlik yedeği oluşturuluyor: {backup_path.name}")

    claude_dir = get_claude_dir()
    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. projects/
        p_dir = get_claude_projects_dir()
        if p_dir.exists():
            for root, _, files in os.walk(p_dir):
                for f in files:
                    full_p = Path(root) / f
                    rel_p = full_p.relative_to(claude_dir)
                    zf.write(full_p, arcname=f"claude/{rel_p.as_posix()}")

        # 2. history.jsonl
        h_file = get_claude_history_file()
        if h_file.exists():
            zf.write(h_file, arcname="claude/history.jsonl")

        # 3. settings.json
        s_file = get_claude_settings_file()
        if s_file.exists():
            zf.write(s_file, arcname="claude/settings.json")

        manifest = {
            "agent": "claude",
            "backup_type": "safety_backup",
            "created_at": datetime.now().isoformat(),
            "source_user_home": str(get_user_home())
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

    _log("✅ Claude güvenlik yedeği başarıyla alındı.")
    return backup_path


def restore_claude_backup(zip_path: Path, log: Optional[Callable[[str], None]] = None) -> Tuple[bool, str]:
    """Claude güvenlik yedeğini geri yükler."""
    def _log(msg: str):
        if log:
            log(msg)

    if not zip_path.exists():
        return False, f"Yedek bulunamadı: {zip_path}"

    if is_claude_running():
        _log("⚠️ Claude açık tespit edildi, kapatılıyor...")
        close_claude_processes()

    _log(f"📥 Claude yedeği geri yükleniyor: {zip_path.name}")

    claude_dir = get_claude_dir()
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.infolist():
                if member.is_dir() or member.filename == "manifest.json":
                    continue
                if member.filename.startswith("claude/"):
                    sub = member.filename[len("claude/"):]
                    target_path = claude_dir / sub
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(target_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)

        _log("✅ Claude yedeği başarıyla geri yüklendi!")
        return True, "Claude yedeği başarıyla geri yüklendi."
    except Exception as e:
        err = f"Claude geri yükleme hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


def clean_claude_conversations(
    take_backup: bool = True,
    force_close: bool = True,
    log: Optional[Callable[[str], None]] = None
) -> Tuple[bool, str]:
    """Claude Code sohbet oturumlarını ve terminal geçmişini sıfırlar."""
    def _log(msg: str):
        if log:
            log(msg)

    if is_claude_running():
        if force_close:
            _log("⚠️ Claude çalışıyor, kapatılıyor...")
            close_claude_processes()
        else:
            return False, "Claude uygulaması açık! Lütfen önce Claude'u kapatın."

    if take_backup:
        try:
            bf = create_claude_safety_backup(log=log)
            _log(f"📁 Güvenlik yedeği kaydedildi: {bf.name}")
        except Exception as e:
            _log(f"⚠️ Claude güvenlik yedeği hatası: {e}")

    _log("🧹 Claude sohbetleri ve oturum geçmişi temizleniyor...")

    # 1. projects/ klasörünü temizle
    p_dir = get_claude_projects_dir()
    if p_dir.exists():
        del_p_count = 0
        for item in p_dir.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink()
                del_p_count += 1
            except Exception:
                pass
        _log(f"  ✓ {del_p_count} adet Claude proje oturum dizini temizlendi.")

    # 2. history.jsonl dosyasını sıfırla
    h_file = get_claude_history_file()
    if h_file.exists():
        try:
            h_file.unlink()
            _log("  ✓ Claude terminal komut geçmişi (history.jsonl) temizlendi.")
        except Exception as e:
            _log(f"  ⚠️ history.jsonl uyarısı: {e}")

    _log("🎉 Claude Code sohbet ve oturumları başarıyla sıfırlandı.")
    return True, "Claude sohbetleri ve oturumları başarıyla temizlendi."


# ==============================================================================
# 3. OPENAI CODEX TEMİZLEME & GERİ YÜKLEME
# ==============================================================================

def create_codex_safety_backup(backup_path: Optional[Path] = None, log: Optional[Callable[[str], None]] = None) -> Path:
    """OpenAI Codex oturumlarını ve geçmişini yedekler."""
    def _log(msg: str):
        if log:
            log(msg)

    if backup_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = get_default_backup_dir() / f"codex_guvenlik_yedegi_{timestamp}.zip"

    _log(f"🛡️ Codex güvenlik yedeği oluşturuluyor: {backup_path.name}")

    codex_dir = get_codex_dir()
    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
        s_dir = get_codex_sessions_dir()
        if s_dir.exists():
            for root, _, files in os.walk(s_dir):
                for f in files:
                    full_p = Path(root) / f
                    rel_p = full_p.relative_to(codex_dir)
                    zf.write(full_p, arcname=f"codex/{rel_p.as_posix()}")

        h_dir = get_codex_history_dir()
        if h_dir.exists():
            for root, _, files in os.walk(h_dir):
                for f in files:
                    full_p = Path(root) / f
                    rel_p = full_p.relative_to(codex_dir)
                    zf.write(full_p, arcname=f"codex/{rel_p.as_posix()}")

        cfg = get_codex_config_file()
        if cfg.exists():
            zf.write(cfg, arcname="codex/config.toml")

        manifest = {
            "agent": "codex",
            "backup_type": "safety_backup",
            "created_at": datetime.now().isoformat(),
            "source_user_home": str(get_user_home())
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

    _log("✅ Codex güvenlik yedeği başarıyla alındı.")
    return backup_path


def restore_codex_backup(zip_path: Path, log: Optional[Callable[[str], None]] = None) -> Tuple[bool, str]:
    """OpenAI Codex yedeğini geri yükler."""
    def _log(msg: str):
        if log:
            log(msg)

    if not zip_path.exists():
        return False, f"Yedek bulunamadı: {zip_path}"

    if is_codex_running():
        _log("⚠️ Codex açık tespit edildi, kapatılıyor...")
        close_codex_processes()

    _log(f"📥 Codex yedeği geri yükleniyor: {zip_path.name}")

    codex_dir = get_codex_dir()
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.infolist():
                if member.is_dir() or member.filename == "manifest.json":
                    continue
                if member.filename.startswith("codex/"):
                    sub = member.filename[len("codex/"):]
                    target_path = codex_dir / sub
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(target_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)

        _log("✅ Codex yedeği başarıyla geri yüklendi!")
        return True, "Codex yedeği başarıyla geri yüklendi."
    except Exception as e:
        err = f"Codex geri yükleme hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


def clean_codex_conversations(
    take_backup: bool = True,
    force_close: bool = True,
    log: Optional[Callable[[str], None]] = None
) -> Tuple[bool, str]:
    """OpenAI Codex sohbet oturumlarını ve komut geçmişini sıfırlar."""
    def _log(msg: str):
        if log:
            log(msg)

    if is_codex_running():
        if force_close:
            _log("⚠️ Codex çalışıyor, kapatılıyor...")
            close_codex_processes()
        else:
            return False, "Codex açık! Lütfen önce Codex'i kapatın."

    if take_backup:
        try:
            bf = create_codex_safety_backup(log=log)
            _log(f"📁 Güvenlik yedeği kaydedildi: {bf.name}")
        except Exception as e:
            _log(f"⚠️ Codex güvenlik yedeği hatası: {e}")

    _log("🧹 Codex oturumları ve geçmişi temizleniyor...")

    # 1. sessions/ klasörünü temizle
    s_dir = get_codex_sessions_dir()
    if s_dir.exists():
        del_count = 0
        for item in s_dir.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink()
                del_count += 1
            except Exception:
                pass
        _log(f"  ✓ {del_count} adet Codex oturum kaydı/klasörü temizlendi.")

    # 2. history/ klasörünü temizle
    h_dir = get_codex_history_dir()
    if h_dir.exists():
        for f in h_dir.glob("*"):
            try:
                f.unlink()
            except Exception:
                pass
        _log("  ✓ Codex prompt geçmişi (history) temizlendi.")

    _log("🎉 Codex oturumları başarıyla sıfırlandı.")
    return True, "Codex oturumları başarıyla temizlendi."


# ==============================================================================
# 4. TÜM ARAÇLARI BİRLİKTE TEMİZLEME (ALL-IN-ONE)
# ==============================================================================

def clean_all_agents(
    take_backup: bool = True,
    force_close: bool = True,
    log: Optional[Callable[[str], None]] = None
) -> Tuple[bool, str]:
    """Antigravity, Claude ve Codex'i tek seferde sıfırlar."""
    def _log(msg: str):
        if log:
            log(msg)

    _log("⚡ TÜM ARAÇLAR (Antigravity, Claude, Codex) SIFIRLANIYOR...")
    s1, m1 = clean_all_conversations_and_projects(take_backup=take_backup, force_close=force_close, log=log)
    s2, m2 = clean_claude_conversations(take_backup=take_backup, force_close=force_close, log=log)
    s3, m3 = clean_codex_conversations(take_backup=take_backup, force_close=force_close, log=log)

    all_success = s1 and s2 and s3
    msg = "Tüm araçların sohbet ve oturumları başarıyla temizlendi." if all_success else "Bazı araçlar temizlenirken uyarılar oluştu."
    return all_success, msg
