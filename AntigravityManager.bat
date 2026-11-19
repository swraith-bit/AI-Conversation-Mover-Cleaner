@echo off
chcp 65001 >nul
title AI Agent Manager • Antigravity ^| Claude ^| Codex
cd /d "%~dp0"
start "" pythonw "%~dp0antigravity_manager.py"
if errorlevel 1 (
    echo [HATA] pythonw calistirilamadi. Konsol modunda python deneniyor...
    python "%~dp0antigravity_manager.py"
    pause
)
