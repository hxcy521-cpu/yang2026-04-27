from pathlib import Path

APP_NAME = "视频素材整理工具"
SUPPORTED_EXTENSIONS = {
    ".mp4", ".mov", ".avi", ".mkv", ".mxf", ".mpg",
    ".mpeg", ".ts", ".wmv", ".flv", ".webm", ".m4v",
}
LOG_DIR = Path("logs")
UNDO_DIR = LOG_DIR / "undo"
APP_LOG_FILE = LOG_DIR / "app.log"

CATEGORY_PRIORITY = [
    "重复文件_待确认",
    "超宽屏素材_5400x1800",
    "4K素材",
    "1080P素材",
    "MOV源文件",
    "MP4成品文件",
    "大文件_10GB以上",
    "短循环素材",
    "其他视频",
]
