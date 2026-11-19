"""
paths.py - Antigravity, Claude Code ve OpenAI Codex dizinleri, dosya yolları ve süreç denetleyicisi.
"""

import os
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional


def get_user_home() -> Path:
    """Kullanıcının ana dizinini döndürür."""
    return Path.home()


# ==========================================
# ANTIGRAVITY YOLLARI
# ==========================================

def get_gemini_dir() -> Path:
    """C:\\Users\\<USER>\\.gemini dizinini döndürür."""
    return get_user_home() / ".gemini"


def get_antigravity_dir() -> Path:
    """C:\\Users\\<USER>\\.gemini\\antigravity dizinini döndürür."""
    return get_gemini_dir() / "antigravity"


def get_conversations_dir() -> Path:
    """Sohbet veritabanlarının (.db) bulunduğu dizin."""
    return get_antigravity_dir() / "conversations"


def get_brain_dir() -> Path:
    """Sohbet logları, transkriptler ve artifact'lerin bulunduğu dizin."""
    return get_antigravity_dir() / "brain"


def get_presence_dir() -> Path:
    """Kilit (.lock) dosyalarının bulunduğu dizin."""
    return get_antigravity_dir() / "presence"


def get_summaries_db() -> Path:
    """conversation_summaries.db SQLite dosya yolu."""
    return get_antigravity_dir() / "conversation_summaries.db"


def get_proto_summaries() -> Path:
    """agyhub_summaries_proto.pb protobuf dosya yolu."""
    return get_antigravity_dir() / "agyhub_summaries_proto.pb"


def get_config_dir() -> Path:
    """C:\\Users\\<USER>\\.gemini\\config dizini."""
    return get_gemini_dir() / "config"


def get_config_projects_dir() -> Path:
    """C:\\Users\\<USER>\\.gemini\\config\\projects dizini."""
    return get_config_dir() / "projects"


def get_projects_json() -> Path:
    """C:\\Users\\<USER>\\.gemini\\projects.json dosya yolu."""
    return get_gemini_dir() / "projects.json"


def get_app_storage_json() -> Path:
    """AppData\\Roaming\\Antigravity\\app_storage.json dosya yolu."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "Antigravity" / "app_storage.json"
    return get_user_home() / "AppData" / "Roaming" / "Antigravity" / "app_storage.json"


def get_config_skills_dir() -> Path:
    """C:\\Users\\<USER>\\.gemini\\config\\skills dizini."""
    return get_config_dir() / "skills"


def get_antigravity_skills_dir() -> Path:
    """C:\\Users\\<USER>\\.gemini\\antigravity\\skills dizini."""
    return get_antigravity_dir() / "skills"


def get_config_plugins_dir() -> Path:
    """C:\\Users\\<USER>\\.gemini\\config\\plugins dizini."""
    return get_config_dir() / "plugins"


def get_antigravity_global_dir() -> Path:
    """C:\\Users\\<USER>\\.antigravity dizini (global kurallar ve ajanlar)."""
    return get_user_home() / ".antigravity"


def is_antigravity_running() -> bool:
    """Antigravity veya Antigravity IDE uygulamasının açık olup olmadığını kontrol eder."""
    try:
        cmd = 'tasklist /FI "IMAGENAME eq Antigravity.exe" /NH'
        output = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
        return "Antigravity.exe" in output
    except Exception:
        return False


def close_antigravity_processes() -> bool:
    """Çalışan Antigravity süreçlerini kapatır."""
    try:
        subprocess.run('taskkill /F /IM Antigravity.exe', shell=True, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


# ==========================================
# CLAUDE CODE & CLAUDE DESKTOP YOLLARI
# ==========================================

def get_claude_dir() -> Path:
    """C:\\Users\\<USER>\\.claude dizinini döndürür."""
    return get_user_home() / ".claude"


def get_claude_projects_dir() -> Path:
    """Sohbet oturumlarının tutulduğu .claude\\projects dizini."""
    return get_claude_dir() / "projects"


def get_claude_history_file() -> Path:
    """.claude\\history.jsonl dosyası (terminal prompt geçmişi)."""
    return get_claude_dir() / "history.jsonl"


def get_claude_skills_dir() -> Path:
    """.claude\\skills dizini."""
    return get_claude_dir() / "skills"


def get_claude_commands_dir() -> Path:
    """.claude\\commands dizini (slash komutları)."""
    return get_claude_dir() / "commands"


def get_claude_agents_dir() -> Path:
    """.claude\\agents dizini (tanımlı alt ajanlar)."""
    return get_claude_dir() / "agents"


def get_claude_plugins_dir() -> Path:
    """.claude\\plugins dizini."""
    return get_claude_dir() / "plugins"


def get_claude_settings_file() -> Path:
    """.claude\\settings.json yapılandırma dosyası."""
    return get_claude_dir() / "settings.json"


def get_claude_config_file() -> Path:
    """~\\.claude.json dosyası (global MCP tanımları)."""
    return get_user_home() / ".claude.json"


def get_claude_md_file() -> Path:
    """.claude\\CLAUDE.md global sistem kuralları dosyası."""
    return get_claude_dir() / "CLAUDE.md"


def get_claude_desktop_dir() -> Path:
    """AppData\\Roaming\\Claude (Claude Desktop uygulaması)."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "Claude"
    return get_user_home() / "AppData" / "Roaming" / "Claude"


def is_claude_running() -> bool:
    """Claude CLI veya Claude Desktop uygulamasının açık olup olmadığını denetler."""
    try:
        cmd = 'tasklist /NH'
        output = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).lower()
        return "claude.exe" in output or "claude-code" in output
    except Exception:
        return False


def close_claude_processes() -> bool:
    """Çalışan Claude süreçlerini güvenle sonlandırır."""
    try:
        subprocess.run('taskkill /F /IM claude.exe', shell=True, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


# ==========================================
# OPENAI CODEX YOLLARI
# ==========================================

def get_codex_dir() -> Path:
    """C:\\Users\\<USER>\\.codex dizinini döndürür."""
    return get_user_home() / ".codex"


def get_codex_sessions_dir() -> Path:
    """Sohbet oturumlarının tutulduğu .codex\\sessions dizini."""
    return get_codex_dir() / "sessions"


def get_codex_history_dir() -> Path:
    """.codex\\history dizini (history.jsonl)."""
    return get_codex_dir() / "history"


def get_codex_skills_dir() -> Path:
    """.codex\\skills dizini."""
    return get_codex_dir() / "skills"


def get_codex_prompts_dir() -> Path:
    """.codex\\prompts dizini."""
    return get_codex_dir() / "prompts"


def get_codex_config_file() -> Path:
    """.codex\\config.toml yapılandırma dosyası."""
    return get_codex_dir() / "config.toml"


def get_codex_agents_md() -> Path:
    """.codex\\AGENTS.md global talimat dosyası."""
    return get_codex_dir() / "AGENTS.md"


def is_codex_running() -> bool:
    """Codex CLI uygulamasının açık olup olmadığını denetler."""
    try:
        cmd = 'tasklist /NH'
        output = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).lower()
        return "codex.exe" in output
    except Exception:
        return False


def close_codex_processes() -> bool:
    """Çalışan Codex süreçlerini sonlandırır."""
    try:
        subprocess.run('taskkill /F /IM codex.exe', shell=True, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


# ==========================================
# YARDIMCI VE İSTATİSTİK FONKSİYONLARI
# ==========================================

def get_folder_size_mb(path: Path) -> float:
    """Dizinin toplam boyutunu MB cinsinden döndürür."""
    if not path.exists():
        return 0.0
    total = 0
    try:
        for p in path.rglob("*"):
            if p.is_file() and not p.is_symlink():
                try:
                    total += p.stat().st_size
                except Exception:
                    pass
    except Exception:
        pass
    return round(total / (1024 * 1024), 2)


def get_file_size_mb(path: Path) -> float:
    """Tek bir dosyanın boyutunu MB cinsinden döndürür."""
    if not path.exists() or not path.is_file():
        return 0.0
    try:
        return round(path.stat().st_size / (1024 * 1024), 2)
    except Exception:
        return 0.0


def get_system_stats() -> Dict[str, Any]:
    """Mevcut sistemdeki Antigravity sohbet, proje ve skills istatistiklerini toplar."""
    convo_count = 0
    db_path = get_summaries_db()
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM conversation_summaries")
            row = cur.fetchone()
            if row:
                convo_count = row[0]
            conn.close()
        except Exception:
            convo_count = len(list(get_conversations_dir().glob("*.db")))
    else:
        convo_count = len(list(get_conversations_dir().glob("*.db")))

    convos_size_mb = get_folder_size_mb(get_conversations_dir())
    brain_size_mb = get_folder_size_mb(get_brain_dir())

    project_count = 0
    projects_dir = get_config_projects_dir()
    if projects_dir.exists():
        for f in projects_dir.glob("*.json"):
            if f.name == "outside-of-project.json":
                continue
            try:
                with open(f, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
                    if "projectResources" in data and data.get("projectResources", {}).get("resources"):
                        project_count += 1
            except Exception:
                pass

    skills = set()
    s_dir1 = get_config_skills_dir()
    if s_dir1.exists():
        for d in s_dir1.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                skills.add(d.name)
    s_dir2 = get_antigravity_skills_dir()
    if s_dir2.exists():
        for d in s_dir2.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                skills.add(d.name)

    return {
        "convo_count": convo_count,
        "convos_size_mb": convos_size_mb,
        "brain_size_mb": brain_size_mb,
        "total_chat_size_mb": round(convos_size_mb + brain_size_mb, 2),
        "project_count": project_count,
        "skills_count": len(skills),
        "skills_list": sorted(list(skills)),
        "is_running": is_antigravity_running(),
        "is_installed": get_gemini_dir().exists() or get_antigravity_dir().exists(),
        "user_home": str(get_user_home())
    }


def get_claude_stats() -> Dict[str, Any]:
    """Claude Code ve Desktop istatistiklerini toplar."""
    claude_dir = get_claude_dir()
    projects_dir = get_claude_projects_dir()
    history_file = get_claude_history_file()

    project_count = 0
    session_count = 0
    if projects_dir.exists():
        for item in projects_dir.iterdir():
            if item.is_dir():
                project_count += 1
                session_count += len(list(item.glob("*.jsonl")))

    chat_size = get_folder_size_mb(projects_dir) + get_file_size_mb(history_file)

    skills = set()
    s_dir = get_claude_skills_dir()
    if s_dir.exists():
        for d in s_dir.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                skills.add(d.name)

    cmd_dir = get_claude_commands_dir()
    cmd_count = len(list(cmd_dir.glob("*.md"))) if cmd_dir.exists() else 0

    return {
        "convo_count": session_count,
        "project_count": project_count,
        "total_chat_size_mb": round(chat_size, 2),
        "skills_count": len(skills),
        "skills_list": sorted(list(skills)),
        "command_count": cmd_count,
        "is_running": is_claude_running(),
        "is_installed": claude_dir.exists() or get_claude_config_file().exists(),
        "user_home": str(get_user_home())
    }


def get_codex_stats() -> Dict[str, Any]:
    """OpenAI Codex istatistiklerini toplar."""
    codex_dir = get_codex_dir()
    sessions_dir = get_codex_sessions_dir()
    history_dir = get_codex_history_dir()

    session_count = 0
    if sessions_dir.exists():
        session_count = len(list(sessions_dir.rglob("*.jsonl")))

    chat_size = get_folder_size_mb(sessions_dir) + get_folder_size_mb(history_dir)

    skills = set()
    s_dir = get_codex_skills_dir()
    if s_dir.exists():
        for d in s_dir.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                skills.add(d.name)

    prompts_dir = get_codex_prompts_dir()
    prompt_count = len(list(prompts_dir.glob("*.md"))) if prompts_dir.exists() else 0

    return {
        "convo_count": session_count,
        "project_count": session_count,
        "total_chat_size_mb": round(chat_size, 2),
        "skills_count": len(skills),
        "skills_list": sorted(list(skills)),
        "prompt_count": prompt_count,
        "is_running": is_codex_running(),
        "is_installed": codex_dir.exists(),
        "user_home": str(get_user_home())
    }


def get_all_agents_stats() -> Dict[str, Any]:
    """Antigravity, Claude ve Codex istatistiklerini bir arada toplar."""
    ant = get_system_stats()
    claude = get_claude_stats()
    codex = get_codex_stats()

    total_convos = ant["convo_count"] + claude["convo_count"] + codex["convo_count"]
    total_size = round(ant["total_chat_size_mb"] + claude["total_chat_size_mb"] + codex["total_chat_size_mb"], 2)
    total_skills = ant["skills_count"] + claude["skills_count"] + codex["skills_count"]

    return {
        "antigravity": ant,
        "claude": claude,
        "codex": codex,
        "total_convos": total_convos,
        "total_size_mb": total_size,
        "total_skills": total_skills,
        "any_running": ant["is_running"] or claude["is_running"] or codex["is_running"]
    }
