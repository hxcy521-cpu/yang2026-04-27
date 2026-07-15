@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ===============================
REM 离线打包脚本（Windows 10）
REM 使用前请将离线依赖包放到 offline_pkgs 目录
REM ===============================

set PKG_DIR=%~dp0offline_pkgs
set DIST_NAME=中文转拼音重命名工具

echo [1/4] 检查离线依赖目录...
if not exist "%PKG_DIR%" (
    echo 错误：未找到离线依赖目录：%PKG_DIR%
    echo 请先把下载好的 whl/tar.gz 文件放入 offline_pkgs 目录。
    pause
    exit /b 1
)

echo [2/4] 离线安装 requirements.txt 依赖...
python -m pip install --no-index --find-links="%PKG_DIR%" -r requirements.txt
if errorlevel 1 (
    echo 错误：离线安装 requirements.txt 失败。
    pause
    exit /b 1
)

echo [3/4] 离线安装 pyinstaller...
python -m pip install --no-index --find-links="%PKG_DIR%" pyinstaller
if errorlevel 1 (
    echo 错误：离线安装 pyinstaller 失败。
    pause
    exit /b 1
)

echo [4/4] 开始打包 EXE...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "%DIST_NAME%" --icon "D3_TOOL_印象视界.ico" main.py
if errorlevel 1 (
    echo 错误：PyInstaller 打包失败。
    pause
    exit /b 1
)

echo.
echo 打包完成！
echo EXE 路径：%~dp0dist\%DIST_NAME%.exe
pause
