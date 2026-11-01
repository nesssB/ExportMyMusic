@echo off
rem Genera dist\ExportMyMusic.exe
cd /d "%~dp0"
".venv\Scripts\pyinstaller.exe" --noconfirm --onefile --windowed --name ExportMyMusic ^
    --collect-data imageio_ffmpeg --collect-submodules yt_dlp --copy-metadata yt-dlp gui.py
pause
