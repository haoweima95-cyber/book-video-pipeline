@echo off
chcp 65001 >nul
title 读书视频流水线 - 环境安装

echo.
echo   ==============================================
echo      读书视频生成流水线 - 环境安装
echo   ==============================================
echo.

echo   [1/5] Checking Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo   [FAIL] Python not found. Install Python 3.10+
    echo          https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo   [OK] Python %%v

echo   [2/5] Checking ffmpeg...
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo   [FAIL] ffmpeg not found. Download and add to PATH:
    echo          https://ffmpeg.org/download.html
    pause
    exit /b 1
)
echo   [OK] ffmpeg ready

echo   [3/5] Installing Python dependencies...
pip install -r "%~dp0requirements.txt" -q
if %errorlevel% neq 0 (
    echo   [FAIL] pip install failed. Check network.
    pause
    exit /b 1
)
echo   [OK] Dependencies installed

echo   [4/5] Installing default voice...
set "VD=%USERPROFILE%\.cosyvoice\voices\默认音色"
if not exist "%VD%" (
    mkdir "%VD%" 2>nul
    copy /Y "%~dp0seed\voice\默认音色\*" "%VD%\" >nul 2>&1
    echo   [OK] Default voice installed
) else (
    echo   [OK] Default voice already exists
)

echo   [5/5] Local CosyVoice model (optional)
echo   ----------------------------------------------
echo   Use local CosyVoice TTS?
echo     [1] Skip - use cloud TTS API (recommended)
echo     [2] Download model (~5.3GB, 20-30 min)
echo       Official: https://github.com/FunAudioLLM/CosyVoice
set /p COSY="  > Enter choice (1/2, default 1): "
if "%COSY%"=="" set COSY=1

if "%COSY%"=="2" (
    echo   Downloading CosyVoice2-0.5B model...
    python -c "from modelscope import snapshot_download; snapshot_download('iic/CosyVoice2-0.5B', cache_dir='%USERPROFILE%\.cache\modelscope')"
    if %errorlevel% equ 0 (
        echo   [OK] Model downloaded
    ) else (
        echo   [WARN] Download failed. You can retry later or use cloud TTS.
    )
)

echo.
echo   ==============================================
echo   Setup complete!
echo   Run in Claude Code: /book-video-pipeline
echo   ==============================================
pause
