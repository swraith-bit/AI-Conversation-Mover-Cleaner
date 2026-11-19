"""
skills_migrator.py - Antigravity, Claude Code ve OpenAI Codex yetenekleri (Skills), eklentileri ve kurallarını taşıma motoru.
"""

import os
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Callable, Optional, Tuple, List

from core.paths import (
    get_config_skills_dir,
    get_antigravity_skills_dir,
    get_config_plugins_dir,
    get_antigravity_global_dir,
    get_claude_dir,
    get_claude_skills_dir,
    get_claude_commands_dir,
    get_claude_agents_dir,
    get_claude_plugins_dir,
    get_claude_md_file,
    get_codex_dir,
    get_codex_skills_dir,
    get_codex_prompts_dir,
    get_codex_config_file,
    get_codex_agents_md,
    get_user_home
)


# ==============================================================================
# 1. ANTIGRAVITY SKILLS TAŞIMA
# ==============================================================================

def export_skills(
    output_zip_path: Path,
    include_plugins: bool = True,
    include_global_rules: bool = True,
    log: Optional[Callable[[str], None]] = None
) -> Tuple[bool, str]:
    """Tüm Antigravity skills'lerini, eklentilerini ve kurallarını zip dosyasına paketler."""
    def _log(msg: str):
        if log:
            log(msg)

    _log(f"⚡ Antigravity skills dışa aktarılıyor: {output_zip_path.name}")
    output_zip_path.parent.mkdir(parents=True, exist_ok=True)

    skills_exported = set()
    plugins_exported = set()

    try:
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            cfg_skills = get_config_skills_dir()
            if cfg_skills.exists():
                for sub in cfg_skills.iterdir():
                    if sub.is_dir() and not sub.name.startswith("."):
                        skills_exported.add(sub.name)
                        for root, _, files in os.walk(sub):
                            for fn in files:
                                fp = Path(root) / fn
                                rel = fp.relative_to(cfg_skills)
                                zf.write(fp, arcname=f"skills/config_skills/{rel.as_posix()}")

            agy_skills = get_antigravity_skills_dir()
            if agy_skills.exists():
                for sub in agy_skills.iterdir():
                    if sub.is_dir() and not sub.name.startswith("."):
                        skills_exported.add(sub.name)
                        for root, _, files in os.walk(sub):
                            for fn in files:
                                fp = Path(root) / fn
                                rel = fp.relative_to(agy_skills)
                                zf.write(fp, arcname=f"skills/antigravity_skills/{rel.as_posix()}")

            if include_plugins:
                cfg_plugins = get_config_plugins_dir()
                if cfg_plugins.exists():
                    for sub in cfg_plugins.iterdir():
                        if sub.is_dir() and not sub.name.startswith("."):
                            plugins_exported.add(sub.name)
                            for root, _, files in os.walk(sub):
                                for fn in files:
                                    fp = Path(root) / fn
                                    rel = fp.relative_to(cfg_plugins)
                                    zf.write(fp, arcname=f"plugins/{rel.as_posix()}")

            if include_global_rules:
                ant_global = get_antigravity_global_dir()
                if ant_global.exists():
                    for root, _, files in os.walk(ant_global):
                        for fn in files:
                            fp = Path(root) / fn
                            rel = fp.relative_to(ant_global)
                            zf.write(fp, arcname=f"global_rules/{rel.as_posix()}")

            manifest = {
                "version": "1.0",
                "export_type": "antigravity_skills",
                "created_at": datetime.now().isoformat(),
                "skills_list": sorted(list(skills_exported)),
                "plugins_list": sorted(list(plugins_exported)),
                "has_global_rules": include_global_rules and get_antigravity_global_dir().exists()
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        _log(f"  ✓ {len(skills_exported)} adet yetenek paketlendi: {', '.join(skills_exported) if skills_exported else 'Yok'}")
        _log(f"✅ Antigravity skills paketi hazırlandı: {output_zip_path.name}")
        return True, "Antigravity skills başarıyla dışa aktarıldı."
    except Exception as e:
        err = f"Skills dışa aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


def import_skills(
    input_zip_path: Path,
    log: Optional[Callable[[str], None]] = None
) -> Tuple[bool, str]:
    """Antigravity skills paketini sisteme yükler."""
    def _log(msg: str):
        if log:
            log(msg)

    if not input_zip_path.exists():
        return False, f"Skills paketi bulunamadı: {input_zip_path}"

    _log(f"📥 Antigravity skills paketi içe aktarılıyor: {input_zip_path.name}")

    try:
        with zipfile.ZipFile(input_zip_path, "r") as zf:
            target_cfg_skills = get_config_skills_dir()
            target_agy_skills = get_antigravity_skills_dir()
            target_plugins = get_config_plugins_dir()
            target_global = get_antigravity_global_dir()

            target_cfg_skills.mkdir(parents=True, exist_ok=True)
            target_agy_skills.mkdir(parents=True, exist_ok=True)
            target_plugins.mkdir(parents=True, exist_ok=True)

            installed_count = 0
            for member in zf.infolist():
                if member.is_dir() or member.filename == "manifest.json":
                    continue

                fn = member.filename
                dest_path = None

                if fn.startswith("skills/config_skills/"):
                    sub = fn[len("skills/config_skills/"):]
                    dest_path = target_cfg_skills / sub
                    dest_path_alt = target_agy_skills / sub
                    dest_path_alt.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(dest_path_alt, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                elif fn.startswith("skills/antigravity_skills/"):
                    sub = fn[len("skills/antigravity_skills/"):]
                    dest_path = target_agy_skills / sub
                elif fn.startswith("plugins/"):
                    sub = fn[len("plugins/"):]
                    dest_path = target_plugins / sub
                elif fn.startswith("global_rules/"):
                    sub = fn[len("global_rules/"):]
                    dest_path = target_global / sub

                if dest_path:
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(dest_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    installed_count += 1

        _log(f"  ✓ Toplam {installed_count} adet dosya kuruldu.")
        _log("🎉 Antigravity skills başarıyla aktarıldı!")
        return True, "Antigravity skills başarıyla içe aktarıldı."
    except Exception as e:
        err = f"Skills içe aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


# ==============================================================================
# 2. CLAUDE CODE SKILLS TAŞIMA
# ==============================================================================

def export_claude_skills(
    output_zip_path: Path,
    log: Optional[Callable[[str], None]] = None
) -> Tuple[bool, str]:
    """Claude Code skills, commands, agents ve CLAUDE.md dosyalarını zip paketine aktarır."""
    def _log(msg: str):
        if log:
            log(msg)

    _log(f"⚡ Claude skills dışa aktarılıyor: {output_zip_path.name}")
    output_zip_path.parent.mkdir(parents=True, exist_ok=True)

    skills_exported = set()
    commands_count = 0

    try:
        claude_dir = get_claude_dir()
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            s_dir = get_claude_skills_dir()
            if s_dir.exists():
                for sub in s_dir.iterdir():
                    if sub.is_dir() and not sub.name.startswith("."):
                        skills_exported.add(sub.name)
                        for root, _, files in os.walk(sub):
                            for fn in files:
                                fp = Path(root) / fn
                                rel = fp.relative_to(claude_dir)
                                zf.write(fp, arcname=f"claude/{rel.as_posix()}")

            c_dir = get_claude_commands_dir()
            if c_dir.exists():
                for root, _, files in os.walk(c_dir):
                    for fn in files:
                        fp = Path(root) / fn
                        rel = fp.relative_to(claude_dir)
                        zf.write(fp, arcname=f"claude/{rel.as_posix()}")
                        commands_count += 1

            a_dir = get_claude_agents_dir()
            if a_dir.exists():
                for root, _, files in os.walk(a_dir):
                    for fn in files:
                        fp = Path(root) / fn
                        rel = fp.relative_to(claude_dir)
                        zf.write(fp, arcname=f"claude/{rel.as_posix()}")

            p_dir = get_claude_plugins_dir()
            if p_dir.exists():
                for root, _, files in os.walk(p_dir):
                    for fn in files:
                        fp = Path(root) / fn
                        rel = fp.relative_to(claude_dir)
                        zf.write(fp, arcname=f"claude/{rel.as_posix()}")

            md_file = get_claude_md_file()
            if md_file.exists():
                zf.write(md_file, arcname="claude/CLAUDE.md")

            manifest = {
                "version": "1.0",
                "export_type": "claude_skills",
                "created_at": datetime.now().isoformat(),
                "skills_list": sorted(list(skills_exported)),
                "commands_count": commands_count,
                "has_claude_md": md_file.exists()
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        _log(f"  ✓ {len(skills_exported)} adet Claude skill, {commands_count} adet komut paketlendi.")
        _log(f"✅ Claude skills paketi hazırlandı: {output_zip_path.name}")
        return True, "Claude skills başarıyla dışa aktarıldı."
    except Exception as e:
        err = f"Claude skills dışa aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


def import_claude_skills(
    input_zip_path: Path,
    log: Optional[Callable[[str], None]] = None
) -> Tuple[bool, str]:
    """Claude Code skills paketini sisteme yükler."""
    def _log(msg: str):
        if log:
            log(msg)

    if not input_zip_path.exists():
        return False, f"Skills paketi bulunamadı: {input_zip_path}"

    _log(f"📥 Claude skills paketi içe aktarılıyor: {input_zip_path.name}")

    try:
        claude_dir = get_claude_dir()
        installed_count = 0

        with zipfile.ZipFile(input_zip_path, "r") as zf:
            for member in zf.infolist():
                if member.is_dir() or member.filename == "manifest.json":
                    continue
                if member.filename.startswith("claude/"):
                    sub = member.filename[len("claude/"):]
                    target_path = claude_dir / sub
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(target_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    installed_count += 1

        _log(f"  ✓ Toplam {installed_count} adet Claude yetenek/komut dosyası kuruldu.")
        _log("🎉 Claude skills başarıyla aktarıldı!")
        return True, "Claude skills başarıyla içe aktarıldı."
    except Exception as e:
        err = f"Claude skills içe aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


# ==============================================================================
# 3. OPENAI CODEX SKILLS TAŞIMA
# ==============================================================================

def export_codex_skills(
    output_zip_path: Path,
    log: Optional[Callable[[str], None]] = None
) -> Tuple[bool, str]:
    """OpenAI Codex skills, prompts, config.toml ve AGENTS.md dosyalarını zip paketine aktarır."""
    def _log(msg: str):
        if log:
            log(msg)

    _log(f"⚡ Codex skills dışa aktarılıyor: {output_zip_path.name}")
    output_zip_path.parent.mkdir(parents=True, exist_ok=True)

    skills_exported = set()
    prompts_count = 0

    try:
        codex_dir = get_codex_dir()
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            s_dir = get_codex_skills_dir()
            if s_dir.exists():
                for sub in s_dir.iterdir():
                    if sub.is_dir() and not sub.name.startswith("."):
                        skills_exported.add(sub.name)
                        for root, _, files in os.walk(sub):
                            for fn in files:
                                fp = Path(root) / fn
                                rel = fp.relative_to(codex_dir)
                                zf.write(fp, arcname=f"codex/{rel.as_posix()}")

            p_dir = get_codex_prompts_dir()
            if p_dir.exists():
                for root, _, files in os.walk(p_dir):
                    for fn in files:
                        fp = Path(root) / fn
                        rel = fp.relative_to(codex_dir)
                        zf.write(fp, arcname=f"codex/{rel.as_posix()}")
                        prompts_count += 1

            cfg = get_codex_config_file()
            if cfg.exists():
                zf.write(cfg, arcname="codex/config.toml")

            agents_md = get_codex_agents_md()
            if agents_md.exists():
                zf.write(agents_md, arcname="codex/AGENTS.md")

            manifest = {
                "version": "1.0",
                "export_type": "codex_skills",
                "created_at": datetime.now().isoformat(),
                "skills_list": sorted(list(skills_exported)),
                "prompts_count": prompts_count,
                "has_config": cfg.exists(),
                "has_agents_md": agents_md.exists()
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        _log(f"  ✓ {len(skills_exported)} adet Codex skill, {prompts_count} adet prompt paketlendi.")
        _log(f"✅ Codex skills paketi hazırlandı: {output_zip_path.name}")
        return True, "Codex skills başarıyla dışa aktarıldı."
    except Exception as e:
        err = f"Codex skills dışa aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


def import_codex_skills(
    input_zip_path: Path,
    log: Optional[Callable[[str], None]] = None
) -> Tuple[bool, str]:
    """OpenAI Codex skills paketini sisteme yükler."""
    def _log(msg: str):
        if log:
            log(msg)

    if not input_zip_path.exists():
        return False, f"Skills paketi bulunamadı: {input_zip_path}"

    _log(f"📥 Codex skills paketi içe aktarılıyor: {input_zip_path.name}")

    try:
        codex_dir = get_codex_dir()
        installed_count = 0

        with zipfile.ZipFile(input_zip_path, "r") as zf:
            for member in zf.infolist():
                if member.is_dir() or member.filename == "manifest.json":
                    continue
                if member.filename.startswith("codex/"):
                    sub = member.filename[len("codex/"):]
                    target_path = codex_dir / sub
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(target_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    installed_count += 1

        _log(f"  ✓ Toplam {installed_count} adet Codex yetenek/ayar dosyası kuruldu.")
        _log("🎉 Codex skills başarıyla aktarıldı!")
        return True, "Codex skills başarıyla içe aktarıldı."
    except Exception as e:
        err = f"Codex skills içe aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


# ==============================================================================
# 4. TÜM ARAÇLARIN SKILLS'LERİNİ BİRLİKTE TAŞIMA (ALL-IN-ONE)
# ==============================================================================

def export_all_agents_skills(
    output_zip_path: Path,
    log: Optional[Callable[[str], None]] = None
) -> Tuple[bool, str]:
    """Antigravity, Claude ve Codex yeteneklerini tek pakette toplar."""
    def _log(msg: str):
        if log:
            log(msg)

    _log("⚡ TÜM ARAÇLAR İÇİN ORTAK SKILLS DIŞA AKTARIMI BAŞLATILIYOR...")
    temp_dir = output_zip_path.parent / "_temp_all_skills_export"
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        f1 = temp_dir / "antigravity_skills.zip"
        f2 = temp_dir / "claude_skills.zip"
        f3 = temp_dir / "codex_skills.zip"

        export_skills(f1, log=log)
        export_claude_skills(f2, log=log)
        export_codex_skills(f3, log=log)

        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if f1.exists():
                zf.write(f1, arcname="packages/antigravity_skills.zip")
            if f2.exists():
                zf.write(f2, arcname="packages/claude_skills.zip")
            if f3.exists():
                zf.write(f3, arcname="packages/codex_skills.zip")

            manifest = {
                "version": "1.0",
                "export_type": "all_agents_skills",
                "created_at": datetime.now().isoformat(),
                "included": ["antigravity", "claude", "codex"]
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        _log(f"🎉 Tüm araçların yetenekleri tek pakette toplandı: {output_zip_path.name}")
        return True, "Tüm araçların skills'leri başarıyla dışa aktarıldı."
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def import_all_agents_skills(
    input_zip_path: Path,
    log: Optional[Callable[[str], None]] = None
) -> Tuple[bool, str]:
    """Tüm araçları içeren ortak skills paketini kurar."""
    def _log(msg: str):
        if log:
            log(msg)

    _log(f"📥 TÜM ARAÇLARIN ORTAK SKILLS PAKETİ KURULUYOR: {input_zip_path.name}")
    temp_dir = input_zip_path.parent / "_temp_all_skills_import"
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(input_zip_path, "r") as zf:
            zf.extractall(temp_dir)

        p1 = temp_dir / "packages" / "antigravity_skills.zip"
        p2 = temp_dir / "packages" / "claude_skills.zip"
        p3 = temp_dir / "packages" / "codex_skills.zip"

        if p1.exists():
            import_skills(p1, log=log)
        if p2.exists():
            import_claude_skills(p2, log=log)
        if p3.exists():
            import_codex_skills(p3, log=log)

        _log("🎉 Tüm araçların yetenekleri başarıyla sisteme kuruldu!")
        return True, "Tüm araçların yetenekleri başarıyla yüklendi."
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
