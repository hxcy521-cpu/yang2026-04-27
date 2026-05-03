# 视频素材整理工具

## 1. 安装依赖
```bash
cd video_organizer
python -m venv venv
# Windows
venv\Scripts\activate
pip install -r requirements.txt
```

## 2. 运行源码
```bash
python main.py
```

## 3. 安装 ffmpeg / ffprobe
- 访问 https://ffmpeg.org/download.html 下载 Windows 版本。
- 解压后将 `ffmpeg/bin` 添加到系统 PATH。
- 打开终端验证：
```bash
ffprobe -version
```
如果没有 ffprobe，程序仍可运行，但只显示基础文件信息。

## 4. 打包 EXE
```bash
build_exe.bat
```
打包后输出：`dist/视频素材整理工具.exe`

## 5. 使用说明
1. 点击“选择文件夹”。
2. 点击“开始扫描”，程序递归扫描支持的视频格式。
3. 可使用筛选：格式、分辨率、大小阈值、重复、关键词。
4. 点击“生成整理规划”，再点击“预览整理结果”。
5. 确认后点击“执行整理”。
6. 如果需要回滚，点击“撤回上一次整理”。
7. 点击“导出报表”导出 CSV/Excel。
8. 如需完整重复检测，单独点击“计算完整重复(Hash)”。

## 6. 支持格式
`mp4 mov avi mkv mxf mpg mpeg ts wmv flv webm m4v`

## 7. 注意事项
- 扫描在线程中进行，避免界面卡死。
- 对损坏文件会记录日志，不会导致程序崩溃。
- 支持中文路径与特殊符号文件名。
- 执行整理会生成 JSON 日志，位于 `logs/undo/`。
- 建议执行整理前先预览并备份重要文件。
