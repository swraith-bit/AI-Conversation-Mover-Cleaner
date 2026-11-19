"""
antigravity_manager.py - Antigravity, Claude Code and OpenAI Codex Chat, Project and Skills Management Tool.
One-click wipe/reset, lossless export/import with path remapping, and skills migration.

Supports both a modern tabbed Desktop Graphical Interface (GUI) and Command Line Interface (CLI).
Multi-language support: English (default) & Turkish.
"""

import os
import sys
import json
import argparse
import threading
from datetime import datetime
from pathlib import Path

# Add core modules to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.paths import (
    get_system_stats,
    get_claude_stats,
    get_codex_stats,
    get_all_agents_stats,
    is_antigravity_running,
    close_antigravity_processes,
    is_claude_running,
    close_claude_processes,
    is_codex_running,
    close_codex_processes,
    get_user_home
)
from core.cleaner import (
    clean_all_conversations_and_projects,
    restore_backup,
    clean_claude_conversations,
    restore_claude_backup,
    clean_codex_conversations,
    restore_codex_backup,
    clean_all_agents,
    get_default_backup_dir
)
from core.chat_migrator import (
    export_chats_and_projects,
    import_chats_and_projects,
    export_claude_chats,
    import_claude_chats,
    export_codex_chats,
    import_codex_chats,
    export_all_agents_chats,
    import_all_agents_chats
)
from core.skills_migrator import (
    export_skills,
    import_skills,
    export_claude_skills,
    import_claude_skills,
    export_codex_skills,
    import_codex_skills,
    export_all_agents_skills,
    import_all_agents_skills
)

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


def load_config() -> dict:
    """Loads configuration file; defaults to English."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"language": "en"}


def save_config(cfg: dict):
    """Saves configuration to config.json."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# ==========================================
# TRANSLATIONS / DİL SÖZLÜĞÜ (i18n)
# ==========================================

TRANSLATIONS = {
    "en": {
        # App
        "app_title": "AI Agent Manager • Antigravity | Claude | Codex",
        "app_subtitle": "v2.0 • Antigravity • Claude • Codex",
        "all_agent_name": "All-in-One",
        # Tabs
        "tab_antigravity": "🚀 Antigravity",
        "tab_claude": "🟣 Claude Code",
        "tab_codex": "🟢 OpenAI Codex",
        "tab_all": "⚡ All-in-One",
        # Stats Bar
        "btn_refresh": "🔄 Refresh",
        "stat_convos_calc": "💬 Chats: Calculating...",
        "stat_convos_fmt": "💬 Chats: {count} items (~{size} MB)",
        "stat_convos_all_fmt": "💬 Total Chats: {count} items (~{size} MB)",
        "stat_projects_fmt": "📁 Projects: {count} items",
        "stat_projects_all_fmt": "📁 Agents: 3 items",
        "stat_skills_fmt": "⚡ Skills: {count}",
        "stat_skills_all_fmt": "⚡ Total Skills: {count}",
        "stat_status_calc": "⚙️ Status: ...",
        "stat_status_running": "⚙️ Status: RUNNING (Active)",
        "stat_status_idle": "⚙️ Status: IDLE (Ready)",
        "stat_status_not_installed": "⚙️ Status: NOT INSTALLED",
        "stat_status_one_running": "⚙️ Status: One is Running",
        "stat_status_all_ready": "⚙️ Status: All Idle (Ready)",
        # Action Column 1: Reset / Clean
        "col1_title": "🧹 1) One-Click Reset",
        "col1_title_all": "🧹 1) Reset All Agents",
        "col1_desc": "Deletes all {agent} chats and sessions.\nTakes an automatic safety backup first.",
        "col1_desc_all": "Resets Antigravity, Claude, and Codex chats\nin one go (creates unified safety backup).",
        "btn_clean": "🔴 Reset {agent} Chats\n(Clean Start)",
        "btn_clean_all": "🔴 Reset All Agents' Chats\n(Total Wipe)",
        "btn_undo": "🛡️ Restore Safety Backup (Undo)",
        "btn_undo_all": "🛡️ Restore Safety Backup",
        # Action Column 2: Chat Migration
        "col2_title": "📦 2) {agent} Chat Migration",
        "col2_title_all": "📦 2) Master Chat Bundle",
        "col2_desc": "Backup chats to .zip to move to another PC\nor import existing chats to this PC.",
        "col2_desc_all": "Combines chats of all agents (Antigravity+Claude+Codex)\ninto a single master .zip package.",
        "btn_export_chats": "📤 Export Chats\n(Create Backup .zip)",
        "btn_export_chats_all": "📤 Export All Chats\n(Master .zip)",
        "btn_import_chats": "📥 Import Chats\n(Load from Another PC)",
        "btn_import_chats_all": "📥 Import Master Bundle\n(Restore All)",
        # Action Column 3: Skills Migration
        "col3_title": "⚡ 3) {agent} Skills Migration",
        "col3_title_all": "⚡ 3) Master Skills Bundle",
        "col3_desc": "Migrate custom skills, commands, rules,\nand subagent setups to another PC.",
        "col3_desc_all": "Packages all agent skills and rule files\ninto a single master .zip archive.",
        "btn_export_skills": "📤 Export Skills\n(Package as .zip)",
        "btn_export_skills_all": "📤 Export All Skills\n(Master .zip)",
        "btn_import_skills": "📥 Import Skills\n(Install on this PC)",
        "btn_import_skills_all": "📥 Install Master Skills\n(Install All on PC)",
        # Terminal & Log Header
        "log_title": "📋 Terminal & Live Activity Log",
        "btn_clear_log": "🧹 Clear Log",
        "btn_copy_log": "📋 Copy Log",
        "log_copied_title": "Copied",
        "log_copied_msg": "All activity logs copied to clipboard!",
        "log_cleared": "Console cleared.",
        "log_init_1": "AI Agent Manager v2.0 successfully started.",
        "log_init_2": "Antigravity, Claude Code, and OpenAI Codex are supported.",
        "log_mode_switched": "Active agent switched: {icon} {name}",
        "log_lang_switched": "Language changed to English.",
        # Dialogs / Popups
        "dialog_success": "Success",
        "dialog_error": "Error",
        "clean_confirm_title": "{agent} Reset Confirmation",
        "clean_confirm_msg": "WARNING!\n\nALL chats and sessions on {agent} will be wiped.\n(An automatic safety backup will be created before wiping).\n\nDo you want to proceed?",
        "clean_log_start": "⏳ {agent} reset process started...",
        "clean_success": "{agent} chats and sessions were cleaned successfully!",
        "clean_error": "Reset failed: {msg}",
        "undo_no_backup_title": "No Backup Found",
        "undo_no_backup_msg": "No automatic safety backup found for {agent}.",
        "undo_confirm_title": "Restore from Safety Backup (Undo)",
        "undo_confirm_msg": "Restore latest safety backup?\n\nFile: {file}\nDate: {date}\n\nThis will roll back your current chats to this snapshot.",
        "undo_log_start": "⏳ Restoring backup: {file}",
        "undo_success": "Backup restored successfully!",
        "undo_error": "Restore failed: {msg}",
        "export_chats_dialog": "Save {agent} Chats (.zip)",
        "export_chats_log_start": "⏳ Exporting {agent} chats...",
        "export_chats_success": "{agent} chats exported successfully:\n{file}",
        "export_chats_error": "Export failed: {msg}",
        "import_chats_dialog": "Select {agent} Backup to Import (.zip)",
        "import_chats_mode_title": "Import Mode",
        "import_chats_mode_msg": "How would you like to restore {agent} backup?\n\n• [YES] = CLEAN REPLACE: Wipes current chats and restores this backup only.\n• [NO] = MERGE: Keeps current chats and merges backup chats alongside them.\n• [CANCEL] = Cancel operation.",
        "import_chats_log_start": "⏳ Importing {agent} chats (Mode: {mode})...",
        "import_chats_success": "{agent} chats imported successfully!\nYou can now start the application.",
        "import_chats_error": "Import failed: {msg}",
        "export_skills_dialog": "Save {agent} Skills Package (.zip)",
        "export_skills_log_start": "⏳ Exporting {agent} skills...",
        "export_skills_success": "{agent} skills packaged successfully:\n{file}",
        "export_skills_error": "Skills export failed: {msg}",
        "import_skills_dialog": "Select {agent} Skills Package to Import (.zip)",
        "import_skills_log_start": "⏳ Installing {agent} skills...",
        "import_skills_success": "{agent} skills installed successfully!",
        "import_skills_error": "Skills installation failed: {msg}",
        # CLI
        "cli_status_antigravity": "\n=== 🚀 ANTIGRAVITY STATUS REPORT ===",
        "cli_status_claude": "\n=== 🟣 CLAUDE CODE STATUS REPORT ===",
        "cli_status_codex": "\n=== 🟢 OPENAI CODEX STATUS REPORT ===",
        "cli_status_all": "\n=== ⚡ ALL AGENTS SUMMARY REPORT ===",
        "cli_user_home": "User Home Directory : {val}",
        "cli_convo_count": "Chat Count          : {val} items",
        "cli_convo_size": "Database Size       : {val} MB",
        "cli_brain_size": "Memory / Log Size   : {val} MB (Brain / Artifacts)",
        "cli_total_size": "Total Chat Size     : {val} MB",
        "cli_project_count": "Project Count       : {val} items",
        "cli_skills_count": "Skills Count        : {val} items ({list})",
        "cli_command_count": "Command Count       : {val} items",
        "cli_prompt_count": "Prompt Count        : {val} items",
        "cli_is_running": "Is Agent Running    : {val}",
        "cli_total_convos": "Total Chats         : {val} items",
        "cli_total_skills": "Total Skills        : {val} items",
        "cli_any_running": "Any Agent Running   : {val}",
        "cli_yes": "YES",
        "cli_no": "NO",
        "cli_clean_starting": "[{agent}] Cleaning chats and sessions...",
        "cli_export_chats_starting": "[{agent}] Exporting chats to: {path}",
        "cli_import_chats_starting": "[{agent}] Importing chats (Mode: {mode}) from: {path}",
        "cli_export_skills_starting": "[{agent}] Exporting skills to: {path}",
        "cli_import_skills_starting": "[{agent}] Installing skills from: {path}",
        "cli_restore_starting": "[{agent}] Restoring backup from: {path}"
    },
    "tr": {
        # App
        "app_title": "AI Agent Manager • Antigravity | Claude | Codex",
        "app_subtitle": "v2.0 • Antigravity • Claude • Codex",
        "all_agent_name": "Hepsi Bir Arada",
        # Tabs
        "tab_antigravity": "🚀 Antigravity",
        "tab_claude": "🟣 Claude Code",
        "tab_codex": "🟢 OpenAI Codex",
        "tab_all": "⚡ Tüm Araçlar",
        # Stats Bar
        "btn_refresh": "🔄 Yenile",
        "stat_convos_calc": "💬 Sohbetler: Hesaplanıyor...",
        "stat_convos_fmt": "💬 Sohbetler: {count} adet (~{size} MB)",
        "stat_convos_all_fmt": "💬 Toplam Sohbet: {count} adet (~{size} MB)",
        "stat_projects_fmt": "📁 Projeler: {count} adet",
        "stat_projects_all_fmt": "📁 Araçlar: 3 adet",
        "stat_skills_fmt": "⚡ Skills: {count}",
        "stat_skills_all_fmt": "⚡ Toplam Skills: {count}",
        "stat_status_calc": "⚙️ Durum: ...",
        "stat_status_running": "⚙️ Durum: AÇIK (Çalışıyor)",
        "stat_status_idle": "⚙️ Durum: KAPALI (Hazır)",
        "stat_status_not_installed": "⚙️ Durum: YÜKLÜ DEĞİL",
        "stat_status_one_running": "⚙️ Durum: Biri Açık (Çalışıyor)",
        "stat_status_all_ready": "⚙️ Durum: Hepsi Kapalı (Hazır)",
        # Action Column 1: Reset / Clean
        "col1_title": "🧹 1) Tek Tuşla Sıfırlama",
        "col1_title_all": "🧹 1) Tüm Araçları Sıfırla",
        "col1_desc": "{agent} sohbet ve oturumlarını siler.\nİşlemden önce otomatik güvenlik yedeği alır.",
        "col1_desc_all": "Antigravity, Claude ve Codex sohbetlerini\ntek hamlede sıfırlar (ortak güvenlik yedeği alır).",
        "btn_clean": "🔴 {agent} Sohbetlerini Sıfırla\n(Temiz Başlangıç)",
        "btn_clean_all": "🔴 Tüm Araçların Sohbetlerini Sıfırla\n(Tam Temizlik)",
        "btn_undo": "🛡️ Son Güvenlik Yedeğinden Geri Al (Undo)",
        "btn_undo_all": "🛡️ Güvenlik Yedeğini Geri Yükle",
        # Action Column 2: Chat Migration
        "col2_title": "📦 2) {agent} Sohbet Taşıma",
        "col2_title_all": "📦 2) Master Sohbet Paketi",
        "col2_desc": "{agent} sohbetlerini başka PC'ye taşımak için\n.zip yedekler veya yeni PC'ye aktarır.",
        "col2_desc_all": "Tüm araçların (Antigravity+Claude+Codex) sohbetlerini\ntek bir .zip dosyasında birleştirir.",
        "btn_export_chats": "📤 Sohbetleri Dışa Aktar\n(Yedek .zip Oluştur)",
        "btn_export_chats_all": "📤 Tüm Sohbetleri Dışa Aktar\n(Master .zip)",
        "btn_import_chats": "📥 Sohbetleri İçe Aktar\n(Başka PC'den Yükle)",
        "btn_import_chats_all": "📥 Master Sohbet Paketini İçe Aktar\n(Tümünü Yükle)",
        # Action Column 3: Skills Migration
        "col3_title": "⚡ 3) {agent} Skills Taşıma",
        "col3_title_all": "⚡ 3) Master Skills Paketi",
        "col3_desc": "{agent} yeteneklerini ve kurallarını\nbaşka bir bilgisayara aktarır veya kurar.",
        "col3_desc_all": "Tüm araçların yeteneklerini ve kurallarını\ntek bir .zip dosyasında toplar.",
        "btn_export_skills": "📤 Skills'leri Dışa Aktar\n(.zip Paketle)",
        "btn_export_skills_all": "📤 Tüm Skills'leri Dışa Aktar\n(Master .zip)",
        "btn_import_skills": "📥 Skills'leri İçe Aktar\n(Başka PC'ye Kur)",
        "btn_import_skills_all": "📥 Master Skills Paketini Kur\n(Tümünü Yükle)",
        # Terminal & Log Header
        "log_title": "📋 Terminal & Canlı Durum Kayıtları",
        "btn_clear_log": "🧹 Konsolu Temizle",
        "btn_copy_log": "📋 Kopyala",
        "log_copied_title": "Kopyalandı",
        "log_copied_msg": "Tüm işlem kayıtları panoya kopyalandı!",
        "log_cleared": "Konsol temizlendi.",
        "log_init_1": "AI Agent Manager v2.0 başarıyla başlatıldı.",
        "log_init_2": "Antigravity, Claude Code ve OpenAI Codex desteklenmektedir.",
        "log_mode_switched": "Mod değiştirildi: {icon} {name}",
        "log_lang_switched": "Dil Türkçe olarak değiştirildi.",
        # Dialogs / Popups
        "dialog_success": "Başarılı",
        "dialog_error": "Hata",
        "clean_confirm_title": "{agent} Sıfırlama Onayı",
        "clean_confirm_msg": "DİKKAT!\n\n{agent} üzerindeki TÜM sohbetler ve oturumlar silinecektir.\n(Silme öncesinde otomatik güvenlik yedeği alınacaktır).\n\nDevam etmek istiyor musunuz?",
        "clean_log_start": "⏳ {agent} sıfırlama işlemi başlatıldı...",
        "clean_success": "{agent} sohbet ve oturumları başarıyla temizlendi!",
        "clean_error": "Sıfırlama başarısız: {msg}",
        "undo_no_backup_title": "Yedek Bulunamadı",
        "undo_no_backup_msg": "{agent} için otomatik alınmış bir güvenlik yedeği bulunamadı.",
        "undo_confirm_title": "Yedekten Geri Alma (Undo)",
        "undo_confirm_msg": "En son güvenlik yedeği geri yüklensin mi?\n\nDosya: {file}\nTarih: {date}\n\nBu işlem mevcut sohbetleri bu yedeğe geri döndürür.",
        "undo_log_start": "⏳ Yedek geri yükleniyor: {file}",
        "undo_success": "Yedek başarıyla geri yüklendi!",
        "undo_error": "Geri alma başarısız: {msg}",
        "export_chats_dialog": "{agent} Sohbetlerini Kaydet (.zip)",
        "export_chats_log_start": "⏳ {agent} sohbetleri dışa aktarılıyor...",
        "export_chats_success": "{agent} sohbetleri başarıyla dışa aktarıldı:\n{file}",
        "export_chats_error": "Dışa aktarma başarısız: {msg}",
        "import_chats_dialog": "İçe Aktarılacak {agent} Yedeğini Seçin (.zip)",
        "import_chats_mode_title": "İçe Aktarma Modu",
        "import_chats_mode_msg": "{agent} yedek içeriği nasıl yüklensin?\n\n• [EVET] = TEMİZ KURULUM: Mevcut sohbetleri temizler ve sadece bu yedeği yükler.\n• [HAYIR] = BİRLEŞTİRME (Merge): Mevcut sohbetleri korur, paketteki sohbetleri onların üzerine ekler.\n• [İPTAL] = İşlemi iptal et.",
        "import_chats_log_start": "⏳ {agent} sohbetleri içe aktarılıyor (Mod: {mode})...",
        "import_chats_success": "{agent} sohbetleri başarıyla aktarıldı!\nUygulamayı başlatabilirsiniz.",
        "import_chats_error": "İçe aktarma başarısız: {msg}",
        "export_skills_dialog": "{agent} Skills Paketini Kaydet (.zip)",
        "export_skills_log_start": "⏳ {agent} skills dışa aktarılıyor...",
        "export_skills_success": "{agent} skills başarıyla paketlendi:\n{file}",
        "export_skills_error": "Skills dışa aktarılamadı: {msg}",
        "import_skills_dialog": "İçe Aktarılacak {agent} Skills Paketini Seçin (.zip)",
        "import_skills_log_start": "⏳ {agent} skills kuruluyor...",
        "import_skills_success": "{agent} skills başarıyla kuruldu!",
        "import_skills_error": "Skills kurulamadı: {msg}",
        # CLI
        "cli_status_antigravity": "\n=== 🚀 ANTIGRAVITY DURUM RAPORU ===",
        "cli_status_claude": "\n=== 🟣 CLAUDE CODE DURUM RAPORU ===",
        "cli_status_codex": "\n=== 🟢 OPENAI CODEX DURUM RAPORU ===",
        "cli_status_all": "\n=== ⚡ TÜM ARAÇLAR ÖZET RAPORU ===",
        "cli_user_home": "Kullanıcı Dizini : {val}",
        "cli_convo_count": "Sohbet Sayısı    : {val} adet",
        "cli_convo_size": "Sohbetler Boyutu : {val} MB (Veritabanları)",
        "cli_brain_size": "Hafıza/Log Boyut : {val} MB (Transkript/Artifacts)",
        "cli_total_size": "Toplam Sohbet    : {val} MB",
        "cli_project_count": "Proje Sayısı     : {val} adet",
        "cli_skills_count": "Skills Sayısı    : {val} adet ({list})",
        "cli_command_count": "Komut Sayısı     : {val} adet",
        "cli_prompt_count": "Prompt Sayısı    : {val} adet",
        "cli_is_running": "Araç Açık mı     : {val}",
        "cli_total_convos": "Toplam Sohbet    : {val} adet",
        "cli_total_skills": "Toplam Skills    : {val} adet",
        "cli_any_running": "Herhangi Biri Açık: {val}",
        "cli_yes": "EVET",
        "cli_no": "HAYIR",
        "cli_clean_starting": "[{agent}] Sohbetler ve oturumlar temizleniyor...",
        "cli_export_chats_starting": "[{agent}] Sohbetler dışa aktarılıyor: {path}",
        "cli_import_chats_starting": "[{agent}] Sohbetler içe aktarılıyor (Mod: {mode}): {path}",
        "cli_export_skills_starting": "[{agent}] Skills dışa aktarılıyor: {path}",
        "cli_import_skills_starting": "[{agent}] Skills kuruluyor: {path}",
        "cli_restore_starting": "[{agent}] Yedek geri yükleniyor: {path}"
    }
}


# ==========================================
# CLI (COMMAND LINE) MODE
# ==========================================

def run_cli(args: argparse.Namespace):
    agent = (args.agent or "antigravity").lower()
    lang = getattr(args, "lang", "en")
    if lang not in TRANSLATIONS:
        lang = "en"
    
    t = TRANSLATIONS[lang]

    def cli_log(msg: str):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    yes_no = lambda b: t["cli_yes"] if b else t["cli_no"]

    if args.status:
        if agent == "antigravity":
            st = get_system_stats()
            print(t["cli_status_antigravity"])
            print(t["cli_user_home"].format(val=st['user_home']))
            print(t["cli_convo_count"].format(val=st['convo_count']))
            print(t["cli_convo_size"].format(val=st['convos_size_mb']))
            print(t["cli_brain_size"].format(val=st['brain_size_mb']))
            print(t["cli_total_size"].format(val=st['total_chat_size_mb']))
            print(t["cli_project_count"].format(val=st['project_count']))
            print(t["cli_skills_count"].format(val=st['skills_count'], list=', '.join(st['skills_list'])))
            print(t["cli_is_running"].format(val=yes_no(st['is_running'])) + "\n")
        elif agent == "claude":
            st = get_claude_stats()
            print(t["cli_status_claude"])
            print(t["cli_user_home"].format(val=st['user_home']))
            print(t["cli_convo_count"].format(val=f"{st['convo_count']} ({st['project_count']} proj)"))
            print(t["cli_total_size"].format(val=st['total_chat_size_mb']))
            print(t["cli_skills_count"].format(val=st['skills_count'], list=', '.join(st['skills_list'])))
            print(t["cli_command_count"].format(val=st['command_count']))
            print(t["cli_is_running"].format(val=yes_no(st['is_running'])) + "\n")
        elif agent == "codex":
            st = get_codex_stats()
            print(t["cli_status_codex"])
            print(t["cli_user_home"].format(val=st['user_home']))
            print(t["cli_convo_count"].format(val=st['convo_count']))
            print(t["cli_total_size"].format(val=st['total_chat_size_mb']))
            print(t["cli_skills_count"].format(val=st['skills_count'], list=', '.join(st['skills_list'])))
            print(t["cli_prompt_count"].format(val=st['prompt_count']))
            print(t["cli_is_running"].format(val=yes_no(st['is_running'])) + "\n")
        elif agent == "all":
            st = get_all_agents_stats()
            print(t["cli_status_all"])
            print(t["cli_total_convos"].format(val=st['total_convos']))
            print(t["cli_total_size"].format(val=st['total_size_mb']))
            print(t["cli_total_skills"].format(val=st['total_skills']))
            print(t["cli_any_running"].format(val=yes_no(st['any_running'])) + "\n")
        return

    if args.clean:
        cli_log(t["cli_clean_starting"].format(agent=agent.upper()))
        if agent == "antigravity":
            s, m = clean_all_conversations_and_projects(take_backup=not args.no_backup, force_close=True, log=cli_log)
        elif agent == "claude":
            s, m = clean_claude_conversations(take_backup=not args.no_backup, force_close=True, log=cli_log)
        elif agent == "codex":
            s, m = clean_codex_conversations(take_backup=not args.no_backup, force_close=True, log=cli_log)
        elif agent == "all":
            s, m = clean_all_agents(take_backup=not args.no_backup, force_close=True, log=cli_log)
        if not s:
            sys.exit(1)
        return

    if args.export_chats:
        out_p = Path(args.export_chats).resolve()
        cli_log(t["cli_export_chats_starting"].format(agent=agent.upper(), path=out_p))
        if agent == "antigravity":
            s, m = export_chats_and_projects(out_p, log=cli_log)
        elif agent == "claude":
            s, m = export_claude_chats(out_p, log=cli_log)
        elif agent == "codex":
            s, m = export_codex_chats(out_p, log=cli_log)
        elif agent == "all":
            s, m = export_all_agents_chats(out_p, log=cli_log)
        if not s:
            sys.exit(1)
        return

    if args.import_chats:
        in_p = Path(args.import_chats).resolve()
        mode = "merge" if args.merge else "replace"
        cli_log(t["cli_import_chats_starting"].format(agent=agent.upper(), mode=mode, path=in_p))
        if agent == "antigravity":
            s, m = import_chats_and_projects(in_p, mode=mode, remap_paths=not args.no_remap, log=cli_log)
        elif agent == "claude":
            s, m = import_claude_chats(in_p, mode=mode, remap_paths=not args.no_remap, log=cli_log)
        elif agent == "codex":
            s, m = import_codex_chats(in_p, mode=mode, remap_paths=not args.no_remap, log=cli_log)
        elif agent == "all":
            s, m = import_all_agents_chats(in_p, mode=mode, remap_paths=not args.no_remap, log=cli_log)
        if not s:
            sys.exit(1)
        return

    if args.export_skills:
        out_p = Path(args.export_skills).resolve()
        cli_log(t["cli_export_skills_starting"].format(agent=agent.upper(), path=out_p))
        if agent == "antigravity":
            s, m = export_skills(out_p, include_plugins=True, include_global_rules=True, log=cli_log)
        elif agent == "claude":
            s, m = export_claude_skills(out_p, log=cli_log)
        elif agent == "codex":
            s, m = export_codex_skills(out_p, log=cli_log)
        elif agent == "all":
            s, m = export_all_agents_skills(out_p, log=cli_log)
        if not s:
            sys.exit(1)
        return

    if args.import_skills:
        in_p = Path(args.import_skills).resolve()
        cli_log(t["cli_import_skills_starting"].format(agent=agent.upper(), path=in_p))
        if agent == "antigravity":
            s, m = import_skills(in_p, log=cli_log)
        elif agent == "claude":
            s, m = import_claude_skills(in_p, log=cli_log)
        elif agent == "codex":
            s, m = import_codex_skills(in_p, log=cli_log)
        elif agent == "all":
            s, m = import_all_agents_skills(in_p, log=cli_log)
        if not s:
            sys.exit(1)
        return

    if args.restore:
        in_p = Path(args.restore).resolve()
        cli_log(t["cli_restore_starting"].format(agent=agent.upper(), path=in_p))
        if agent == "claude":
            s, m = restore_claude_backup(in_p, log=cli_log)
        elif agent == "codex":
            s, m = restore_codex_backup(in_p, log=cli_log)
        else:
            s, m = restore_backup(in_p, log=cli_log)
        if not s:
            sys.exit(1)
        return


# ==========================================
# GUI (MODERN TABBED & CARD DESIGN)
# ==========================================

import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter.scrolledtext import ScrolledText


class ModernAgentManagerApp:
        def __init__(self, root: tk.Tk):
            self.root = root
            self.config = load_config()
            self.lang = self.config.get("language", "en")
            if self.lang not in TRANSLATIONS:
                self.lang = "en"

            self.root.title(self.t("app_title"))
            self.root.geometry("1040x750")
            self.root.minsize(920, 650)

            # Modern Dark Theme Color Palette (Dark Slate Obsidian)
            self.BG_MAIN = "#0b0c10"
            self.BG_HEADER = "#12141c"
            self.BG_CARD = "#171924"
            self.BG_CARD_LIGHT = "#1e2130"
            self.BG_CARD_HOVER = "#262a3d"
            self.BORDER_COLOR = "#25293a"
            self.BORDER_SUBTLE = "#1e2230"

            self.FG_TITLE = "#f8fafc"
            self.FG_MAIN = "#e2e8f0"
            self.FG_MUTED = "#94a3b8"
            self.FG_SUBTLE = "#64748b"

            # Agent Color Themes
            self.THEMES = {
                "antigravity": {
                    "name": "Antigravity",
                    "icon": "🚀",
                    "accent": "#38bdf8",
                    "accent_hover": "#0ea5e9",
                    "accent_dark": "#0369a1",
                    "badge_bg": "#082f49",
                    "badge_fg": "#7dd3fc"
                },
                "claude": {
                    "name": "Claude Code",
                    "icon": "🟣",
                    "accent": "#f97316",
                    "accent_hover": "#ea580c",
                    "accent_dark": "#c2410c",
                    "badge_bg": "#431407",
                    "badge_fg": "#fdba74"
                },
                "codex": {
                    "name": "OpenAI Codex",
                    "icon": "🟢",
                    "accent": "#10b981",
                    "accent_hover": "#059669",
                    "accent_dark": "#047857",
                    "badge_bg": "#022c22",
                    "badge_fg": "#6ee7b7"
                },
                "all": {
                    "name": self.t("all_agent_name"),
                    "icon": "⚡",
                    "accent": "#a855f7",
                    "accent_hover": "#9333ea",
                    "accent_dark": "#7e22ce",
                    "badge_bg": "#3b0764",
                    "badge_fg": "#d8b4fe"
                }
            }

            self.current_agent = "antigravity"
            self.tab_buttons = {}
            self.latest_stats_data = {}

            self.root.configure(bg=self.BG_MAIN)
            self._build_ui()
            self.switch_agent("antigravity")
            self._update_lang_buttons()

        def t(self, key: str, **kwargs) -> str:
            """Translates key to current language with formatting."""
            template = TRANSLATIONS.get(self.lang, {}).get(key, key)
            if kwargs:
                try:
                    return template.format(**kwargs)
                except Exception:
                    return template
            return template

        def set_language(self, new_lang: str):
            """Switches the interface language."""
            if new_lang not in TRANSLATIONS or new_lang == self.lang:
                return
            self.lang = new_lang
            self.config["language"] = new_lang
            save_config(self.config)

            # Update All-in-One theme name
            self.THEMES["all"]["name"] = self.t("all_agent_name")

            self._update_lang_buttons()
            self._update_all_texts()
            self.log(self.t("log_lang_switched"), "SUCCESS")

        def _update_lang_buttons(self):
            """Updates visual state of language toggle buttons."""
            if self.lang == "en":
                self.btn_lang_en.config(bg="#38bdf8", fg="#0b0c10")
                self.btn_lang_tr.config(bg=self.BG_CARD_LIGHT, fg=self.FG_MUTED)
            else:
                self.btn_lang_en.config(bg=self.BG_CARD_LIGHT, fg=self.FG_MUTED)
                self.btn_lang_tr.config(bg="#38bdf8", fg="#0b0c10")

        def _update_all_texts(self):
            """Updates all text elements in the GUI when language changes."""
            self.root.title(self.t("app_title"))
            self.subtitle_lbl.config(text=self.t("app_subtitle"))

            # Tab text updates
            self.tab_buttons["antigravity"].config(text=f" {self.t('tab_antigravity')} ")
            self.tab_buttons["claude"].config(text=f" {self.t('tab_claude')} ")
            self.tab_buttons["codex"].config(text=f" {self.t('tab_codex')} ")
            self.tab_buttons["all"].config(text=f" {self.t('tab_all')} ")

            # Refresh button & log buttons
            self.btn_refresh.config(text=self.t("btn_refresh"))
            self.log_title.config(text=self.t("log_title"))
            self.btn_clear_log.config(text=self.t("btn_clear_log"))
            self.btn_copy_log.config(text=self.t("btn_copy_log"))

            # Update current active agent card texts
            self._apply_agent_card_texts(self.current_agent)

            # Update stats display if we have cached stats
            if self.latest_stats_data:
                self._update_stats_ui(self.current_agent, self.latest_stats_data)
            else:
                self.refresh_stats()

        def _build_ui(self):
            # 1. Top Navigation Bar (Header)
            top_bar = tk.Frame(self.root, bg=self.BG_HEADER, height=64)
            top_bar.pack(fill=tk.X, side=tk.TOP)

            brand_frame = tk.Frame(top_bar, bg=self.BG_HEADER)
            brand_frame.pack(side=tk.LEFT, padx=18, pady=12)

            title_icon = tk.Label(
                brand_frame,
                text="⚡",
                font=("Segoe UI Emoji", 16),
                bg=self.BG_HEADER,
                fg="#f59e0b"
            )
            title_icon.pack(side=tk.LEFT, padx=(0, 6))

            title_lbl = tk.Label(
                brand_frame,
                text="AI Agent Manager",
                font=("Segoe UI", 14, "bold"),
                fg=self.FG_TITLE,
                bg=self.BG_HEADER
            )
            title_lbl.pack(side=tk.LEFT)

            self.subtitle_lbl = tk.Label(
                brand_frame,
                text=self.t("app_subtitle"),
                font=("Segoe UI", 8),
                fg=self.FG_MUTED,
                bg=self.BG_HEADER
            )
            self.subtitle_lbl.pack(side=tk.LEFT, padx=8, pady=(4, 0))

            # Right side container: Tabs + Language Switcher
            right_header = tk.Frame(top_bar, bg=self.BG_HEADER)
            right_header.pack(side=tk.RIGHT, padx=16, pady=10)

            # Language Switcher (Segmented EN / TR buttons)
            lang_container = tk.Frame(
                right_header,
                bg=self.BG_CARD_LIGHT,
                highlightthickness=1,
                highlightbackground=self.BORDER_COLOR,
                padx=2,
                pady=2
            )
            lang_container.pack(side=tk.RIGHT, padx=(10, 0))

            self.btn_lang_en = tk.Label(
                lang_container,
                text=" EN ",
                font=("Segoe UI", 8, "bold"),
                bg="#38bdf8",
                fg="#0b0c10",
                padx=6,
                pady=3,
                cursor="hand2",
                relief=tk.FLAT
            )
            self.btn_lang_en.pack(side=tk.LEFT)
            self.btn_lang_en.bind("<Button-1>", lambda e: self.set_language("en"))

            self.btn_lang_tr = tk.Label(
                lang_container,
                text=" TR ",
                font=("Segoe UI", 8, "bold"),
                bg=self.BG_CARD_LIGHT,
                fg=self.FG_MUTED,
                padx=6,
                pady=3,
                cursor="hand2",
                relief=tk.FLAT
            )
            self.btn_lang_tr.pack(side=tk.LEFT)
            self.btn_lang_tr.bind("<Button-1>", lambda e: self.set_language("tr"))

            # Tab Buttons (Pill Tabs)
            tabs_frame = tk.Frame(right_header, bg=self.BG_HEADER)
            tabs_frame.pack(side=tk.RIGHT)

            tab_items = [
                ("antigravity", "tab_antigravity"),
                ("claude", "tab_claude"),
                ("codex", "tab_codex"),
                ("all", "tab_all")
            ]

            for key, t_key in tab_items:
                btn = tk.Label(
                    tabs_frame,
                    text=f" {self.t(t_key)} ",
                    font=("Segoe UI", 9, "bold"),
                    bg=self.BG_CARD,
                    fg=self.FG_MUTED,
                    padx=10,
                    pady=6,
                    cursor="hand2",
                    relief=tk.FLAT
                )
                btn.pack(side=tk.LEFT, padx=3)
                btn.bind("<Button-1>", lambda e, k=key: self.switch_agent(k))
                btn.bind("<Enter>", lambda e, b=btn, k=key: self._on_tab_hover(b, k, True))
                btn.bind("<Leave>", lambda e, b=btn, k=key: self._on_tab_hover(b, k, False))
                self.tab_buttons[key] = btn

            # Subtle separator line
            sep = tk.Frame(self.root, bg=self.BORDER_COLOR, height=1)
            sep.pack(fill=tk.X)

            # 2. Stats & Metric Card
            self.stats_card = tk.Frame(
                self.root,
                bg=self.BG_CARD,
                highlightthickness=1,
                highlightbackground=self.BORDER_COLOR,
                padx=16,
                pady=12
            )
            self.stats_card.pack(fill=tk.X, padx=16, pady=(12, 6))

            # Metric Labels
            self.lbl_stat_agent = tk.Label(
                self.stats_card,
                text="🚀 Antigravity",
                font=("Segoe UI", 11, "bold"),
                fg="#38bdf8",
                bg=self.BG_CARD
            )
            self.lbl_stat_agent.grid(row=0, column=0, sticky="w", padx=(0, 16))

            self.lbl_stat_convos = tk.Label(
                self.stats_card,
                text=self.t("stat_convos_calc"),
                font=("Segoe UI", 9, "bold"),
                fg="#93c5fd",
                bg=self.BG_CARD
            )
            self.lbl_stat_convos.grid(row=0, column=1, sticky="w", padx=10)

            self.lbl_stat_projects = tk.Label(
                self.stats_card,
                text="📁 ...",
                font=("Segoe UI", 9, "bold"),
                fg="#34d399",
                bg=self.BG_CARD
            )
            self.lbl_stat_projects.grid(row=0, column=2, sticky="w", padx=10)

            self.lbl_stat_skills = tk.Label(
                self.stats_card,
                text="⚡ ...",
                font=("Segoe UI", 9, "bold"),
                fg="#fbbf24",
                bg=self.BG_CARD
            )
            self.lbl_stat_skills.grid(row=0, column=3, sticky="w", padx=10)

            self.lbl_stat_status = tk.Label(
                self.stats_card,
                text=self.t("stat_status_calc"),
                font=("Segoe UI", 9, "bold"),
                fg="#a78bfa",
                bg=self.BG_CARD
            )
            self.lbl_stat_status.grid(row=0, column=4, sticky="w", padx=10)

            self.stats_card.grid_columnconfigure(5, weight=1)

            self.btn_refresh = tk.Button(
                self.stats_card,
                text=self.t("btn_refresh"),
                command=self.refresh_stats,
                font=("Segoe UI", 8, "bold"),
                bg=self.BG_CARD_LIGHT,
                fg=self.FG_MAIN,
                activebackground=self.BG_CARD_HOVER,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                cursor="hand2",
                padx=10,
                pady=4
            )
            self.btn_refresh.grid(row=0, column=6, sticky="e")
            self._add_button_hover(self.btn_refresh, self.BG_CARD_LIGHT, self.BG_CARD_HOVER)

            # 3. Main Action Cards Container
            self.actions_container = tk.Frame(self.root, bg=self.BG_MAIN)
            self.actions_container.pack(fill=tk.X, padx=16, pady=6)

            self._build_action_cards()

            # 4. Modern Terminal / Live Process Console
            log_container = tk.Frame(
                self.root,
                bg=self.BG_CARD,
                highlightthickness=1,
                highlightbackground=self.BORDER_COLOR,
                padx=12,
                pady=10
            )
            log_container.pack(fill=tk.BOTH, expand=True, padx=16, pady=(6, 12))

            log_header = tk.Frame(log_container, bg=self.BG_CARD)
            log_header.pack(fill=tk.X, pady=(0, 6))

            self.log_title = tk.Label(
                log_header,
                text=self.t("log_title"),
                font=("Segoe UI", 9, "bold"),
                fg=self.FG_MUTED,
                bg=self.BG_CARD
            )
            self.log_title.pack(side=tk.LEFT)

            self.btn_clear_log = tk.Button(
                log_header,
                text=self.t("btn_clear_log"),
                command=self.clear_logs,
                font=("Segoe UI", 8),
                bg=self.BG_CARD_LIGHT,
                fg=self.FG_MUTED,
                activebackground=self.BG_CARD_HOVER,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                cursor="hand2",
                padx=8,
                pady=2
            )
            self.btn_clear_log.pack(side=tk.RIGHT, padx=(4, 0))
            self._add_button_hover(self.btn_clear_log, self.BG_CARD_LIGHT, self.BG_CARD_HOVER)

            self.btn_copy_log = tk.Button(
                log_header,
                text=self.t("btn_copy_log"),
                command=self.copy_logs,
                font=("Segoe UI", 8),
                bg=self.BG_CARD_LIGHT,
                fg=self.FG_MUTED,
                activebackground=self.BG_CARD_HOVER,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                cursor="hand2",
                padx=8,
                pady=2
            )
            self.btn_copy_log.pack(side=tk.RIGHT)
            self._add_button_hover(self.btn_copy_log, self.BG_CARD_LIGHT, self.BG_CARD_HOVER)

            # ScrolledText
            self.txt_log = ScrolledText(
                log_container,
                wrap=tk.WORD,
                font=("Consolas", 9),
                bg="#08090d",
                fg="#cbd5e1",
                insertbackground="#38bdf8",
                relief=tk.FLAT,
                padx=10,
                pady=8
            )
            self.txt_log.pack(fill=tk.BOTH, expand=True)

            # Console Tag Styles
            self.txt_log.tag_config("TIME", foreground="#64748b")
            self.txt_log.tag_config("AGENT", foreground="#38bdf8", font=("Consolas", 9, "bold"))
            self.txt_log.tag_config("SUCCESS", foreground="#34d399", font=("Consolas", 9, "bold"))
            self.txt_log.tag_config("WARNING", foreground="#fbbf24", font=("Consolas", 9, "bold"))
            self.txt_log.tag_config("ERROR", foreground="#f87171", font=("Consolas", 9, "bold"))
            self.txt_log.tag_config("INFO", foreground="#e2e8f0")

            self.log(self.t("log_init_1"))
            self.log(self.t("log_init_2"))

        def _build_action_cards(self):
            """Builds the 3-column action cards layout."""
            # Column 1: Reset & Clean
            self.col1 = tk.Frame(
                self.actions_container,
                bg=self.BG_CARD,
                highlightthickness=1,
                highlightbackground=self.BORDER_COLOR,
                padx=14,
                pady=12
            )
            self.col1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

            self.lbl_col1_title = tk.Label(
                self.col1,
                text="",
                font=("Segoe UI", 10, "bold"),
                fg="#fca5a5",
                bg=self.BG_CARD
            )
            self.lbl_col1_title.pack(anchor="w", pady=(0, 4))

            self.lbl_col1_desc = tk.Label(
                self.col1,
                text="",
                font=("Segoe UI", 8),
                fg=self.FG_MUTED,
                bg=self.BG_CARD,
                justify=tk.LEFT
            )
            self.lbl_col1_desc.pack(anchor="w", pady=(0, 10))

            self.btn_clean = tk.Button(
                self.col1,
                text="",
                command=self.action_clean,
                font=("Segoe UI", 9, "bold"),
                bg="#991b1b",
                fg="#ffffff",
                activebackground="#b91c1c",
                activeforeground="#ffffff",
                relief=tk.FLAT,
                cursor="hand2",
                pady=8
            )
            self.btn_clean.pack(fill=tk.X, pady=(0, 8))
            self._add_button_hover(self.btn_clean, "#991b1b", "#b91c1c")

            self.btn_undo = tk.Button(
                self.col1,
                text="",
                command=self.action_undo,
                font=("Segoe UI", 8),
                bg=self.BG_CARD_LIGHT,
                fg=self.FG_MAIN,
                activebackground=self.BG_CARD_HOVER,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                cursor="hand2",
                pady=5
            )
            self.btn_undo.pack(fill=tk.X)
            self._add_button_hover(self.btn_undo, self.BG_CARD_LIGHT, self.BG_CARD_HOVER)

            # Column 2: Chat Migration (Export/Import)
            self.col2 = tk.Frame(
                self.actions_container,
                bg=self.BG_CARD,
                highlightthickness=1,
                highlightbackground=self.BORDER_COLOR,
                padx=14,
                pady=12
            )
            self.col2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

            self.lbl_col2_title = tk.Label(
                self.col2,
                text="",
                font=("Segoe UI", 10, "bold"),
                fg="#93c5fd",
                bg=self.BG_CARD
            )
            self.lbl_col2_title.pack(anchor="w", pady=(0, 4))

            self.lbl_col2_desc = tk.Label(
                self.col2,
                text="",
                font=("Segoe UI", 8),
                fg=self.FG_MUTED,
                bg=self.BG_CARD,
                justify=tk.LEFT
            )
            self.lbl_col2_desc.pack(anchor="w", pady=(0, 10))

            self.btn_export_chats = tk.Button(
                self.col2,
                text="",
                command=self.action_export_chats,
                font=("Segoe UI", 9, "bold"),
                bg="#1d4ed8",
                fg="#ffffff",
                activebackground="#2563eb",
                activeforeground="#ffffff",
                relief=tk.FLAT,
                cursor="hand2",
                pady=6
            )
            self.btn_export_chats.pack(fill=tk.X, pady=(0, 8))
            self._add_button_hover(self.btn_export_chats, "#1d4ed8", "#2563eb")

            self.btn_import_chats = tk.Button(
                self.col2,
                text="",
                command=self.action_import_chats,
                font=("Segoe UI", 9, "bold"),
                bg="#047857",
                fg="#ffffff",
                activebackground="#059669",
                activeforeground="#ffffff",
                relief=tk.FLAT,
                cursor="hand2",
                pady=6
            )
            self.btn_import_chats.pack(fill=tk.X)
            self._add_button_hover(self.btn_import_chats, "#047857", "#059669")

            # Column 3: Skills Migration (Export/Import)
            self.col3 = tk.Frame(
                self.actions_container,
                bg=self.BG_CARD,
                highlightthickness=1,
                highlightbackground=self.BORDER_COLOR,
                padx=14,
                pady=12
            )
            self.col3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

            self.lbl_col3_title = tk.Label(
                self.col3,
                text="",
                font=("Segoe UI", 10, "bold"),
                fg="#fde68a",
                bg=self.BG_CARD
            )
            self.lbl_col3_title.pack(anchor="w", pady=(0, 4))

            self.lbl_col3_desc = tk.Label(
                self.col3,
                text="",
                font=("Segoe UI", 8),
                fg=self.FG_MUTED,
                bg=self.BG_CARD,
                justify=tk.LEFT
            )
            self.lbl_col3_desc.pack(anchor="w", pady=(0, 10))

            self.btn_export_skills = tk.Button(
                self.col3,
                text="",
                command=self.action_export_skills,
                font=("Segoe UI", 9, "bold"),
                bg="#b45309",
                fg="#ffffff",
                activebackground="#d97706",
                activeforeground="#ffffff",
                relief=tk.FLAT,
                cursor="hand2",
                pady=6
            )
            self.btn_export_skills.pack(fill=tk.X, pady=(0, 8))
            self._add_button_hover(self.btn_export_skills, "#b45309", "#d97706")

            self.btn_import_skills = tk.Button(
                self.col3,
                text="",
                command=self.action_import_skills,
                font=("Segoe UI", 9, "bold"),
                bg="#0f766e",
                fg="#ffffff",
                activebackground="#0d9488",
                activeforeground="#ffffff",
                relief=tk.FLAT,
                cursor="hand2",
                pady=6
            )
            self.btn_import_skills.pack(fill=tk.X)
            self._add_button_hover(self.btn_import_skills, "#0f766e", "#0d9488")

        def _add_button_hover(self, btn: tk.Widget, normal_bg: str, hover_bg: str):
            btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
            btn.bind("<Leave>", lambda e: btn.config(bg=normal_bg))

        def _on_tab_hover(self, btn: tk.Label, key: str, is_enter: bool):
            if key == self.current_agent:
                return
            if is_enter:
                btn.config(bg=self.BG_CARD_HOVER, fg=self.FG_TITLE)
            else:
                btn.config(bg=self.BG_CARD, fg=self.FG_MUTED)

        # ==================== TAB SWITCHING ====================

        def switch_agent(self, agent_key: str):
            """Changes active agent tab and refreshes cards & stats."""
            self.current_agent = agent_key
            theme = self.THEMES[agent_key]

            # Update tab button visuals
            for k, btn in self.tab_buttons.items():
                if k == agent_key:
                    btn.config(
                        bg=theme["accent_dark"],
                        fg="#ffffff",
                        font=("Segoe UI", 9, "bold")
                    )
                else:
                    btn.config(
                        bg=self.BG_CARD,
                        fg=self.FG_MUTED,
                        font=("Segoe UI", 9)
                    )

            # Update stats agent label
            self.lbl_stat_agent.config(
                text=f"{theme['icon']} {theme['name']}",
                fg=theme["accent"]
            )

            # Adapt card texts and buttons to active agent
            self._apply_agent_card_texts(agent_key)

            self.log(self.t("log_mode_switched", icon=theme['icon'], name=theme['name']))
            self.refresh_stats()

        def _apply_agent_card_texts(self, agent_key: str):
            """Applies translated texts to the 3 action cards for selected agent."""
            theme = self.THEMES[agent_key]
            name = theme["name"]

            if agent_key == "all":
                self.lbl_col1_title.config(text=self.t("col1_title_all"))
                self.lbl_col1_desc.config(text=self.t("col1_desc_all"))
                self.btn_clean.config(text=self.t("btn_clean_all"))
                self.btn_undo.config(text=self.t("btn_undo_all"))

                self.lbl_col2_title.config(text=self.t("col2_title_all"))
                self.lbl_col2_desc.config(text=self.t("col2_desc_all"))
                self.btn_export_chats.config(text=self.t("btn_export_chats_all"))
                self.btn_import_chats.config(text=self.t("btn_import_chats_all"))

                self.lbl_col3_title.config(text=self.t("col3_title_all"))
                self.lbl_col3_desc.config(text=self.t("col3_desc_all"))
                self.btn_export_skills.config(text=self.t("btn_export_skills_all"))
                self.btn_import_skills.config(text=self.t("btn_import_skills_all"))
            else:
                self.lbl_col1_title.config(text=self.t("col1_title"))
                self.lbl_col1_desc.config(text=self.t("col1_desc", agent=name))
                self.btn_clean.config(text=self.t("btn_clean", agent=name))
                self.btn_undo.config(text=self.t("btn_undo"))

                self.lbl_col2_title.config(text=self.t("col2_title", agent=name))
                self.lbl_col2_desc.config(text=self.t("col2_desc", agent=name))
                self.btn_export_chats.config(text=self.t("btn_export_chats"))
                self.btn_import_chats.config(text=self.t("btn_import_chats"))

                self.lbl_col3_title.config(text=self.t("col3_title", agent=name))
                self.lbl_col3_desc.config(text=self.t("col3_desc", agent=name))
                self.btn_export_skills.config(text=self.t("btn_export_skills"))
                self.btn_import_skills.config(text=self.t("btn_import_skills"))

        # ==================== LOGS & STATS ====================

        def log(self, msg: str, tag: str = "INFO"):
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.root.after(0, self._append_log, timestamp, msg, tag)

        def _append_log(self, timestamp: str, msg: str, tag: str):
            self.txt_log.insert(tk.END, f"[{timestamp}] ", "TIME")
            agent_theme = self.THEMES[self.current_agent]
            self.txt_log.insert(tk.END, f"[{agent_theme['name']}] ", "AGENT")

            tag_to_use = tag
            lower_msg = msg.lower()
            if "✓" in msg or "success" in lower_msg or "başarılı" in lower_msg:
                tag_to_use = "SUCCESS"
            elif "⚠️" in msg or "warning" in lower_msg or "uyarı" in lower_msg:
                tag_to_use = "WARNING"
            elif "❌" in msg or "error" in lower_msg or "failed" in lower_msg or "hata" in lower_msg:
                tag_to_use = "ERROR"

            self.txt_log.insert(tk.END, f"{msg}\n", tag_to_use)
            self.txt_log.see(tk.END)

        def clear_logs(self):
            self.txt_log.delete("1.0", tk.END)
            self.log(self.t("log_cleared"))

        def copy_logs(self):
            logs = self.txt_log.get("1.0", tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(logs)
            messagebox.showinfo(self.t("log_copied_title"), self.t("log_copied_msg"))

        def refresh_stats(self):
            def _worker():
                agent = self.current_agent
                if agent == "antigravity":
                    data = get_system_stats()
                elif agent == "claude":
                    data = get_claude_stats()
                elif agent == "codex":
                    data = get_codex_stats()
                else:
                    data = get_all_agents_stats()
                self.latest_stats_data = data
                self.root.after(0, self._update_stats_ui, agent, data)

            threading.Thread(target=_worker, daemon=True).start()

        def _update_stats_ui(self, agent: str, data: dict):
            if agent != self.current_agent:
                return

            if agent == "all":
                self.lbl_stat_convos.config(
                    text=self.t("stat_convos_all_fmt", count=data['total_convos'], size=data['total_size_mb'])
                )
                self.lbl_stat_projects.config(text=self.t("stat_projects_all_fmt"))
                unit = "items" if self.lang == "en" else "adet"
                self.lbl_stat_skills.config(text=self.t("stat_skills_all_fmt", count=f"{data['total_skills']} {unit}"))
                if data["any_running"]:
                    self.lbl_stat_status.config(text=self.t("stat_status_one_running"), fg="#fbbf24")
                else:
                    self.lbl_stat_status.config(text=self.t("stat_status_all_ready"), fg="#34d399")
            else:
                self.lbl_stat_convos.config(
                    text=self.t("stat_convos_fmt", count=data['convo_count'], size=data['total_chat_size_mb'])
                )
                self.lbl_stat_projects.config(
                    text=self.t("stat_projects_fmt", count=data['project_count'])
                )
                unit = "items" if self.lang == "en" else "adet"
                s_txt = f"{data['skills_count']} {unit}"
                if data.get("skills_list"):
                    s_txt += f" ({', '.join(data['skills_list'])})"
                self.lbl_stat_skills.config(text=self.t("stat_skills_fmt", count=s_txt))

                if data["is_running"]:
                    self.lbl_stat_status.config(text=self.t("stat_status_running"), fg="#fbbf24")
                elif not data.get("is_installed", True):
                    self.lbl_stat_status.config(text=self.t("stat_status_not_installed"), fg="#94a3b8")
                else:
                    self.lbl_stat_status.config(text=self.t("stat_status_idle"), fg="#34d399")

        # ==================== ACTIONS ====================

        def action_clean(self):
            agent = self.current_agent
            theme = self.THEMES[agent]

            confirm = messagebox.askyesno(
                self.t("clean_confirm_title", agent=theme['name']),
                self.t("clean_confirm_msg", agent=theme['name']),
                icon="warning"
            )
            if not confirm:
                return

            def _clean_worker():
                self.log(self.t("clean_log_start", agent=theme['name']))
                if agent == "antigravity":
                    success, msg = clean_all_conversations_and_projects(take_backup=True, force_close=True, log=self.log)
                elif agent == "claude":
                    success, msg = clean_claude_conversations(take_backup=True, force_close=True, log=self.log)
                elif agent == "codex":
                    success, msg = clean_codex_conversations(take_backup=True, force_close=True, log=self.log)
                elif agent == "all":
                    success, msg = clean_all_agents(take_backup=True, force_close=True, log=self.log)

                self.refresh_stats()
                if success:
                    self.root.after(0, lambda: messagebox.showinfo(
                        self.t("dialog_success"),
                        self.t("clean_success", agent=theme['name'])
                    ))
                else:
                    self.root.after(0, lambda: messagebox.showerror(
                        self.t("dialog_error"),
                        self.t("clean_error", msg=msg)
                    ))

            threading.Thread(target=_clean_worker, daemon=True).start()

        def action_undo(self):
            agent = self.current_agent
            backup_dir = get_default_backup_dir()

            if agent == "claude":
                pattern = "claude_guvenlik_yedegi_*.zip"
            elif agent == "codex":
                pattern = "codex_guvenlik_yedegi_*.zip"
            elif agent == "all":
                pattern = "all_agents_guvenlik_yedegi_*.zip"
            else:
                pattern = "antigravity_guvenlik_yedegi_*.zip"

            backups = sorted(list(backup_dir.glob(pattern)), key=os.path.getmtime, reverse=True)
            if not backups:
                backups = sorted(list(backup_dir.glob("guvenlik_yedegi_*.zip")), key=os.path.getmtime, reverse=True)

            if not backups:
                messagebox.showinfo(
                    self.t("undo_no_backup_title"),
                    self.t("undo_no_backup_msg", agent=self.THEMES[agent]['name'])
                )
                return

            latest_backup = backups[0]
            dt_str = datetime.fromtimestamp(latest_backup.stat().st_mtime).strftime('%d.%m.%Y %H:%M:%S')

            confirm = messagebox.askyesno(
                self.t("undo_confirm_title"),
                self.t("undo_confirm_msg", file=latest_backup.name, date=dt_str),
                icon="question"
            )
            if not confirm:
                return

            def _undo_worker():
                self.log(self.t("undo_log_start", file=latest_backup.name))
                if agent == "claude":
                    success, msg = restore_claude_backup(latest_backup, log=self.log)
                elif agent == "codex":
                    success, msg = restore_codex_backup(latest_backup, log=self.log)
                else:
                    success, msg = restore_backup(latest_backup, log=self.log)

                self.refresh_stats()
                if success:
                    self.root.after(0, lambda: messagebox.showinfo(self.t("dialog_success"), self.t("undo_success")))
                else:
                    self.root.after(0, lambda: messagebox.showerror(self.t("dialog_error"), self.t("undo_error", msg=msg)))

            threading.Thread(target=_undo_worker, daemon=True).start()

        def action_export_chats(self):
            agent = self.current_agent
            theme = self.THEMES[agent]
            default_fn = f"{agent}_chats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

            save_path = filedialog.asksaveasfilename(
                title=self.t("export_chats_dialog", agent=theme['name']),
                initialfile=default_fn,
                defaultextension=".zip",
                filetypes=[("Zip Archives", "*.zip"), ("All Files", "*.*")]
            )
            if not save_path:
                return

            out_p = Path(save_path)

            def _exp_worker():
                self.log(self.t("export_chats_log_start", agent=theme['name']))
                if agent == "antigravity":
                    success, msg = export_chats_and_projects(out_p, log=self.log)
                elif agent == "claude":
                    success, msg = export_claude_chats(out_p, log=self.log)
                elif agent == "codex":
                    success, msg = export_codex_chats(out_p, log=self.log)
                elif agent == "all":
                    success, msg = export_all_agents_chats(out_p, log=self.log)

                if success:
                    self.root.after(0, lambda: messagebox.showinfo(
                        self.t("dialog_success"),
                        self.t("export_chats_success", agent=theme['name'], file=out_p.name)
                    ))
                else:
                    self.root.after(0, lambda: messagebox.showerror(
                        self.t("dialog_error"),
                        self.t("export_chats_error", msg=msg)
                    ))

            threading.Thread(target=_exp_worker, daemon=True).start()

        def action_import_chats(self):
            agent = self.current_agent
            theme = self.THEMES[agent]

            file_path = filedialog.askopenfilename(
                title=self.t("import_chats_dialog", agent=theme['name']),
                filetypes=[("Zip Archives", "*.zip"), ("All Files", "*.*")]
            )
            if not file_path:
                return

            in_p = Path(file_path)

            mode_choice = messagebox.askyesnocancel(
                self.t("import_chats_mode_title"),
                self.t("import_chats_mode_msg", agent=theme['name'])
            )
            if mode_choice is None:
                return

            import_mode = "replace" if mode_choice else "merge"

            def _imp_worker():
                self.log(self.t("import_chats_log_start", agent=theme['name'], mode=import_mode.upper()))
                if agent == "antigravity":
                    success, msg = import_chats_and_projects(in_p, mode=import_mode, remap_paths=True, log=self.log)
                elif agent == "claude":
                    success, msg = import_claude_chats(in_p, mode=import_mode, remap_paths=True, log=self.log)
                elif agent == "codex":
                    success, msg = import_codex_chats(in_p, mode=import_mode, remap_paths=True, log=self.log)
                elif agent == "all":
                    success, msg = import_all_agents_chats(in_p, mode=import_mode, remap_paths=True, log=self.log)

                self.refresh_stats()
                if success:
                    self.root.after(0, lambda: messagebox.showinfo(
                        self.t("dialog_success"),
                        self.t("import_chats_success", agent=theme['name'])
                    ))
                else:
                    self.root.after(0, lambda: messagebox.showerror(
                        self.t("dialog_error"),
                        self.t("import_chats_error", msg=msg)
                    ))

            threading.Thread(target=_imp_worker, daemon=True).start()

        def action_export_skills(self):
            agent = self.current_agent
            theme = self.THEMES[agent]
            default_fn = f"{agent}_skills_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

            save_path = filedialog.asksaveasfilename(
                title=self.t("export_skills_dialog", agent=theme['name']),
                initialfile=default_fn,
                defaultextension=".zip",
                filetypes=[("Zip Archives", "*.zip"), ("All Files", "*.*")]
            )
            if not save_path:
                return

            out_p = Path(save_path)

            def _exp_sk_worker():
                self.log(self.t("export_skills_log_start", agent=theme['name']))
                if agent == "antigravity":
                    success, msg = export_skills(out_p, include_plugins=True, include_global_rules=True, log=self.log)
                elif agent == "claude":
                    success, msg = export_claude_skills(out_p, log=self.log)
                elif agent == "codex":
                    success, msg = export_codex_skills(out_p, log=self.log)
                elif agent == "all":
                    success, msg = export_all_agents_skills(out_p, log=self.log)

                if success:
                    self.root.after(0, lambda: messagebox.showinfo(
                        self.t("dialog_success"),
                        self.t("export_skills_success", agent=theme['name'], file=out_p.name)
                    ))
                else:
                    self.root.after(0, lambda: messagebox.showerror(
                        self.t("dialog_error"),
                        self.t("export_skills_error", msg=msg)
                    ))

            threading.Thread(target=_exp_sk_worker, daemon=True).start()

        def action_import_skills(self):
            agent = self.current_agent
            theme = self.THEMES[agent]

            file_path = filedialog.askopenfilename(
                title=self.t("import_skills_dialog", agent=theme['name']),
                filetypes=[("Zip Archives", "*.zip"), ("All Files", "*.*")]
            )
            if not file_path:
                return

            in_p = Path(file_path)

            def _imp_sk_worker():
                self.log(self.t("import_skills_log_start", agent=theme['name']))
                if agent == "antigravity":
                    success, msg = import_skills(in_p, log=self.log)
                elif agent == "claude":
                    success, msg = import_claude_skills(in_p, log=self.log)
                elif agent == "codex":
                    success, msg = import_codex_skills(in_p, log=self.log)
                elif agent == "all":
                    success, msg = import_all_agents_skills(in_p, log=self.log)

                self.refresh_stats()
                if success:
                    self.root.after(0, lambda: messagebox.showinfo(
                        self.t("dialog_success"),
                        self.t("import_skills_success", agent=theme['name'])
                    ))
                else:
                    self.root.after(0, lambda: messagebox.showerror(
                        self.t("dialog_error"),
                        self.t("import_skills_error", msg=msg)
                    ))

            threading.Thread(target=_imp_sk_worker, daemon=True).start()


def run_gui():
    root = tk.Tk()
    app = ModernAgentManagerApp(root)
    root.mainloop()


# ==========================================
# MAIN RUNNER
# ==========================================

def main():
    parser = argparse.ArgumentParser(
        description="AI Agent Manager • Antigravity, Claude Code & OpenAI Codex Management Tool"
    )
    parser.add_argument(
        "--agent",
        choices=["antigravity", "claude", "codex", "all"],
        default="antigravity",
        help="Target AI agent (default: antigravity)"
    )
    parser.add_argument(
        "--lang",
        choices=["en", "tr"],
        default="en",
        help="Interface and output language (default: en)"
    )
    parser.add_argument("--status", action="store_true", help="Print current status and metric reports")
    parser.add_argument("--clean", action="store_true", help="Reset/wipe chats and sessions of selected agent")
    parser.add_argument("--no-backup", action="store_true", help="Skip automatic safety backup before clean")
    parser.add_argument("--export-chats", metavar="ZIP_PATH", help="Export chats to specified ZIP file")
    parser.add_argument("--import-chats", metavar="ZIP_PATH", help="Import chats from specified ZIP file")
    parser.add_argument("--merge", action="store_true", help="Preserve existing chats and merge during import")
    parser.add_argument("--no-remap", action="store_true", help="Disable automatic username path remapping")
    parser.add_argument("--export-skills", metavar="ZIP_PATH", help="Export skills to specified ZIP file")
    parser.add_argument("--import-skills", metavar="ZIP_PATH", help="Import skills from specified ZIP file")
    parser.add_argument("--restore", metavar="ZIP_PATH", help="Restore specified safety backup file")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode directly without GUI")

    args = parser.parse_args()

    cli_flags = [args.status, args.clean, args.export_chats, args.import_chats, args.export_skills, args.import_skills, args.restore, args.cli]
    if any(cli_flags):
        run_cli(args)
    else:
        run_gui()


if __name__ == "__main__":
    main()
