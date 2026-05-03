@echo off
chcp 65001 >nul
cd /d %~dp0
if not exist venv (
  python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt
pyinstaller --noconfirm --clean --windowed --name 视频素材整理工具 main.py
echo Build done. Output: dist\视频素材整理工具.exe
pause
