@echo off
chcp 65001 >nul
title AI Agent Manager - Antigravity | Claude | Codex
cd /d "%~dp0"

if exist "%~dp0AntigravityManager.exe" (
    start "" "%~dp0AntigravityManager.exe"
    exit /b 0
)

where python >nul 2>&1
if errorlevel 1 goto :missing_python

python -B -c "import tkinter" >nul 2>&1
if not errorlevel 1 goto :launch_app

echo [!] Python kurulu ancak Tkinter (tcl/tk) modulu bulunamadi.
echo [!] Python installed, but Tkinter (tcl/tk) module is missing.
echo.
goto :offer_install

:missing_python
echo [!] Bu bilgisayarda Python bulunamadi.
echo [!] Python was not found on this PC.
echo.

:offer_install
where winget >nul 2>&1
if errorlevel 1 (
    echo Lutfen https://www.python.org/downloads/ adresinden Python 3.12+ yukleyin
    echo ve kurulumda "Add python.exe to PATH" + "tcl/tk" seceneklerini isaretleyin.
    pause
    exit /b 1
)

set /p INSTALL_CHOICE="Python (Tkinter dahil) otomatik yuklensin mi? / Auto-install Python with Tkinter? [E/Y/N]: "
if /i "%INSTALL_CHOICE%"=="E" goto :do_winget
if /i "%INSTALL_CHOICE%"=="Y" goto :do_winget
exit /b 1

:do_winget
echo Python 3.12 yukleniyor, lutfen bekleyin... / Installing Python 3.12, please wait...
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo [HATA] Otomatik kurulum basarisiz oldu. Lutfen python.org uzerinden manuel yukleyin.
    pause
    exit /b 1
)

set "PY312=%LocalAppData%\Programs\Python\Python312\pythonw.exe"
if exist "%PY312%" (
    start "" "%PY312%" "%~dp0antigravity_manager.py"
    exit /b 0
)

echo Kurulum tamamlandi. Pencereyi kapatip AntigravityManager.bat dosyasini yeniden baslatin.
pause
exit /b 0

:launch_app
where pythonw >nul 2>&1
if not errorlevel 1 (
    start "" pythonw "%~dp0antigravity_manager.py"
    exit /b 0
)
python -B "%~dp0antigravity_manager.py"
if errorlevel 1 pause
