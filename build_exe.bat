@echo off
chcp 65001 >nul

REM Windows 10 下打包为单文件、无控制台窗口的 GUI 程序
python -m PyInstaller --noconfirm --clean --onefile --windowed --name PinyinRenamer main.py

echo.
echo 打包完成，输出文件在 dist\PinyinRenamer.exe
pause
