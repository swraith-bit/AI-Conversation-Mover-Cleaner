"""
skills_migrator.py - Antigravity, Claude Code ve OpenAI Codex yetenekleri (Skills), eklentileri ve kurallarını taşıma motoru.
"""

import os
import json
import zlib
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Callable, Optional, Tuple, List

from core.zip_utils import (
    atomic_zip_write,
    collect_dir_entries,
    extract_zip_with_progress,
    fs_path,
    write_entries_to_zip,
)

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
    log: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
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
        entries: List[Tuple[Path, str, int]] = []

        cfg_skills = get_config_skills_dir()
        if cfg_skills.exists():
            for sub in cfg_skills.iterdir():
                if sub.is_dir() and not sub.name.startswith("."):
                    skills_exported.add(sub.name)
                    entries.extend(collect_dir_entries(sub, "skills/config_skills", base_dir=cfg_skills))

        agy_skills = get_antigravity_skills_dir()
        if agy_skills.exists():
            for sub in agy_skills.iterdir():
                if sub.is_dir() and not sub.name.startswith("."):
                    skills_exported.add(sub.name)
                    entries.extend(collect_dir_entries(sub, "skills/antigravity_skills", base_dir=agy_skills))

        if include_plugins:
            cfg_plugins = get_config_plugins_dir()
            if cfg_plugins.exists():
                for sub in cfg_plugins.iterdir():
                    if sub.is_dir() and not sub.name.startswith("."):
                        plugins_exported.add(sub.name)
                        entries.extend(collect_dir_entries(sub, "plugins", base_dir=cfg_plugins))

        if include_global_rules:
            ant_global = get_antigravity_global_dir()
            if ant_global.exists():
                entries.extend(collect_dir_entries(ant_global, "global_rules", base_dir=ant_global))

        def _write(zf: zipfile.ZipFile):
            write_entries_to_zip(zf, entries, progress_callback=progress_callback, log=log)
            manifest = {
                "version": "1.0",
                "export_type": "antigravity_skills",
                "created_at": datetime.now().isoformat(),
                "skills_list": sorted(list(skills_exported)),
                "plugins_list": sorted(list(plugins_exported)),
                "has_global_rules": include_global_rules and get_antigravity_global_dir().exists()
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        atomic_zip_write(output_zip_path, _write)

        _log(f"  ✓ {len(skills_exported)} adet yetenek paketlendi: {', '.join(skills_exported) if skills_exported else 'Yok'}")
        _log(f"✅ Antigravity skills paketi hazırlandı: {output_zip_path.name}")
        return True, "Antigravity skills başarıyla dışa aktarıldı."
    except Exception as e:
        err = f"Skills dışa aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


def import_skills(
    input_zip_path: Path,
    log: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
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

            members = [m for m in zf.infolist() if not m.is_dir() and m.filename != "manifest.json"]
            total_bytes = sum(m.file_size for m in members) or 1
            done_bytes = 0
            installed_count = 0

            for member in members:
                fn = member.filename
                dest_path = None

                if fn.startswith("skills/config_skills/"):
                    sub = fn[len("skills/config_skills/"):]
                    dest_path = target_cfg_skills / sub
                    dest_path_alt = target_agy_skills / sub
                    os.makedirs(fs_path(dest_path_alt.parent), exist_ok=True)
                    with zf.open(member) as src, open(fs_path(dest_path_alt), "wb") as dst:
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
                    os.makedirs(fs_path(dest_path.parent), exist_ok=True)
                    with zf.open(member) as src, open(fs_path(dest_path), "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    installed_count += 1

                done_bytes += member.file_size
                if progress_callback:
                    progress_callback(done_bytes, total_bytes)

        _log(f"  ✓ Toplam {installed_count} adet dosya kuruldu.")
        _log("🎉 Antigravity skills başarıyla aktarıldı!")
        return True, "Antigravity skills başarıyla içe aktarıldı."
    except (zipfile.BadZipFile, zlib.error, EOFError) as e:
        err = f"Bozuk veya geçersiz ZIP dosyası (zip corrupted): {str(e)}"
        _log(f"❌ {err}")
        return False, err
    except Exception as e:
        err = f"Skills içe aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


# ==============================================================================
# 2. CLAUDE CODE SKILLS TAŞIMA
# ==============================================================================

def export_claude_skills(
    output_zip_path: Path,
    log: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
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
        entries: List[Tuple[Path, str, int]] = []

        s_dir = get_claude_skills_dir()
        if s_dir.exists():
            for sub in s_dir.iterdir():
                if sub.is_dir() and not sub.name.startswith("."):
                    skills_exported.add(sub.name)
                    entries.extend(collect_dir_entries(sub, "claude", base_dir=claude_dir))

        c_dir = get_claude_commands_dir()
        if c_dir.exists():
            cmd_entries = collect_dir_entries(c_dir, "claude", base_dir=claude_dir)
            commands_count = len(cmd_entries)
            entries.extend(cmd_entries)

        a_dir = get_claude_agents_dir()
        if a_dir.exists():
            entries.extend(collect_dir_entries(a_dir, "claude", base_dir=claude_dir))

        p_dir = get_claude_plugins_dir()
        if p_dir.exists():
            entries.extend(collect_dir_entries(p_dir, "claude", base_dir=claude_dir))

        md_file = get_claude_md_file()
        if md_file.exists() and md_file.is_file():
            entries.append((md_file, "claude/CLAUDE.md", md_file.stat().st_size))

        def _write(zf: zipfile.ZipFile):
            write_entries_to_zip(zf, entries, progress_callback=progress_callback, log=log)
            manifest = {
                "version": "1.0",
                "export_type": "claude_skills",
                "created_at": datetime.now().isoformat(),
                "skills_list": sorted(list(skills_exported)),
                "commands_count": commands_count,
                "has_claude_md": md_file.exists()
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        atomic_zip_write(output_zip_path, _write)

        _log(f"  ✓ {len(skills_exported)} adet Claude skill, {commands_count} adet komut paketlendi.")
        _log(f"✅ Claude skills paketi hazırlandı: {output_zip_path.name}")
        return True, "Claude skills başarıyla dışa aktarıldı."
    except Exception as e:
        err = f"Claude skills dışa aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


def import_claude_skills(
    input_zip_path: Path,
    log: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
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
            members = [m for m in zf.infolist() if not m.is_dir() and m.filename != "manifest.json"]
            total_bytes = sum(m.file_size for m in members) or 1
            done_bytes = 0
            for member in members:
                if member.filename.startswith("claude/"):
                    sub = member.filename[len("claude/"):]
                    target_path = claude_dir / sub
                    os.makedirs(fs_path(target_path.parent), exist_ok=True)
                    with zf.open(member) as src, open(fs_path(target_path), "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    installed_count += 1
                done_bytes += member.file_size
                if progress_callback:
                    progress_callback(done_bytes, total_bytes)

        _log(f"  ✓ Toplam {installed_count} adet Claude yetenek/komut dosyası kuruldu.")
        _log("🎉 Claude skills başarıyla aktarıldı!")
        return True, "Claude skills başarıyla içe aktarıldı."
    except (zipfile.BadZipFile, zlib.error, EOFError) as e:
        err = f"Bozuk veya geçersiz ZIP dosyası (zip corrupted): {str(e)}"
        _log(f"❌ {err}")
        return False, err
    except Exception as e:
        err = f"Claude skills içe aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


# ==============================================================================
# 3. OPENAI CODEX SKILLS TAŞIMA
# ==============================================================================

def export_codex_skills(
    output_zip_path: Path,
    log: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
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
        entries: List[Tuple[Path, str, int]] = []

        s_dir = get_codex_skills_dir()
        if s_dir.exists():
            for sub in s_dir.iterdir():
                if sub.is_dir() and not sub.name.startswith("."):
                    skills_exported.add(sub.name)
                    entries.extend(collect_dir_entries(sub, "codex", base_dir=codex_dir))

        p_dir = get_codex_prompts_dir()
        if p_dir.exists():
            p_entries = collect_dir_entries(p_dir, "codex", base_dir=codex_dir)
            prompts_count = len(p_entries)
            entries.extend(p_entries)

        cfg = get_codex_config_file()
        if cfg.exists() and cfg.is_file():
            entries.append((cfg, "codex/config.toml", cfg.stat().st_size))

        agents_md = get_codex_agents_md()
        if agents_md.exists() and agents_md.is_file():
            entries.append((agents_md, "codex/AGENTS.md", agents_md.stat().st_size))

        def _write(zf: zipfile.ZipFile):
            write_entries_to_zip(zf, entries, progress_callback=progress_callback, log=log)
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

        atomic_zip_write(output_zip_path, _write)

        _log(f"  ✓ {len(skills_exported)} adet Codex skill, {prompts_count} adet prompt paketlendi.")
        _log(f"✅ Codex skills paketi hazırlandı: {output_zip_path.name}")
        return True, "Codex skills başarıyla dışa aktarıldı."
    except Exception as e:
        err = f"Codex skills dışa aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


def import_codex_skills(
    input_zip_path: Path,
    log: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
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
            members = [m for m in zf.infolist() if not m.is_dir() and m.filename != "manifest.json"]
            total_bytes = sum(m.file_size for m in members) or 1
            done_bytes = 0
            for member in members:
                if member.filename.startswith("codex/"):
                    sub = member.filename[len("codex/"):]
                    target_path = codex_dir / sub
                    os.makedirs(fs_path(target_path.parent), exist_ok=True)
                    with zf.open(member) as src, open(fs_path(target_path), "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    installed_count += 1
                done_bytes += member.file_size
                if progress_callback:
                    progress_callback(done_bytes, total_bytes)

        _log(f"  ✓ Toplam {installed_count} adet Codex yetenek/ayar dosyası kuruldu.")
        _log("🎉 Codex skills başarıyla aktarıldı!")
        return True, "Codex skills başarıyla içe aktarıldı."
    except (zipfile.BadZipFile, zlib.error, EOFError) as e:
        err = f"Bozuk veya geçersiz ZIP dosyası (zip corrupted): {str(e)}"
        _log(f"❌ {err}")
        return False, err
    except Exception as e:
        err = f"Codex skills içe aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


# ==============================================================================
# 4. TÜM ARAÇLARIN SKILLS'LERİNİ BİRLİKTE TAŞIMA (ALL-IN-ONE)
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
        cb(offset + int(span * min(1.0, done / max(sub_total, 1))), total)
    return _inner


def export_all_agents_skills(
    output_zip_path: Path,
    log: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Tuple[bool, str]:
    """Antigravity, Claude ve Codex yeteneklerini tek pakette toplar."""
    def _log(msg: str):
        if log:
            log(msg)

    _log("⚡ TÜM ARAÇLAR İÇİN ORTAK SKILLS DIŞA AKTARIMI BAŞLATILIYOR...")

    try:
        with tempfile.TemporaryDirectory(prefix="agm_all_sk_exp_") as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            f1 = temp_dir / "antigravity_skills.zip"
            f2 = temp_dir / "claude_skills.zip"
            f3 = temp_dir / "codex_skills.zip"

            ok1, err1 = export_skills(f1, log=log, progress_callback=_scaled_progress(progress_callback, 0, 33, 100))
            if not ok1:
                return False, err1
            ok2, err2 = export_claude_skills(f2, log=log, progress_callback=_scaled_progress(progress_callback, 33, 33, 100))
            if not ok2:
                return False, err2
            ok3, err3 = export_codex_skills(f3, log=log, progress_callback=_scaled_progress(progress_callback, 66, 34, 100))
            if not ok3:
                return False, err3

            pkg_entries: List[Tuple[Path, str, int]] = []
            for fp, arc in [(f1, "packages/antigravity_skills.zip"), (f2, "packages/claude_skills.zip"), (f3, "packages/codex_skills.zip")]:
                if fp.exists():
                    pkg_entries.append((fp, arc, fp.stat().st_size))

            def _write(zf: zipfile.ZipFile):
                write_entries_to_zip(zf, pkg_entries, log=log)
                manifest = {
                    "version": "1.0",
                    "export_type": "all_agents_skills",
                    "created_at": datetime.now().isoformat(),
                    "included": ["antigravity", "claude", "codex"]
                }
                zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            atomic_zip_write(output_zip_path, _write)
            if progress_callback:
                progress_callback(100, 100)

        _log(f"🎉 Tüm araçların yetenekleri tek pakette toplandı: {output_zip_path.name}")
        return True, "Tüm araçların skills'leri başarıyla dışa aktarıldı."
    except Exception as e:
        err = f"Toplu skills dışa aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err


def import_all_agents_skills(
    input_zip_path: Path,
    log: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Tuple[bool, str]:
    """Tüm araçları içeren ortak skills paketini kurar."""
    def _log(msg: str):
        if log:
            log(msg)

    if not input_zip_path.exists():
        return False, f"Skills paketi bulunamadı: {input_zip_path}"

    _log(f"📥 TÜM ARAÇLARIN ORTAK SKILLS PAKETİ KURULUYOR: {input_zip_path.name}")

    try:
        with tempfile.TemporaryDirectory(prefix="agm_all_sk_imp_") as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            extract_zip_with_progress(
                input_zip_path,
                temp_dir,
                progress_callback=_scaled_progress(progress_callback, 0, 20, 100),
            )

            p1 = temp_dir / "packages" / "antigravity_skills.zip"
            p2 = temp_dir / "packages" / "claude_skills.zip"
            p3 = temp_dir / "packages" / "codex_skills.zip"

            sub_jobs = [(p1, import_skills), (p2, import_claude_skills), (p3, import_codex_skills)]
            existing = [(p, fn, max(p.stat().st_size, 1)) for p, fn in sub_jobs if p.exists()]
            total_sz = sum(sz for _, _, sz in existing) or 1
            offset = 20

            for p, fn, sz in existing:
                span = max(1, int(80 * sz / total_sz))
                ok, err = fn(p, log=log, progress_callback=_scaled_progress(progress_callback, offset, span, 100))
                if not ok:
                    return False, err
                offset += span

            if progress_callback:
                progress_callback(100, 100)

        _log("🎉 Tüm araçların yetenekleri başarıyla sisteme kuruldu!")
        return True, "Tüm araçların yetenekleri başarıyla yüklendi."
    except (zipfile.BadZipFile, zlib.error, EOFError) as e:
        err = f"Bozuk veya geçersiz ZIP dosyası (zip corrupted): {str(e)}"
        _log(f"❌ {err}")
        return False, err
    except Exception as e:
        err = f"Toplu skills içe aktarma hatası: {str(e)}"
        _log(f"❌ {err}")
        return False, err
