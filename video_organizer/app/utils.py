import logging
from datetime import datetime
from pathlib import Path

from .config import APP_LOG_FILE, LOG_DIR, UNDO_DIR


def ensure_dirs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    UNDO_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging() -> None:
    ensure_dirs()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(APP_LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def format_size(num_bytes: int) -> str:
    gb = 1024 ** 3
    mb = 1024 ** 2
    if num_bytes >= gb:
        return f"{num_bytes / gb:.2f} GB"
    return f"{num_bytes / mb:.2f} MB"


def ts_to_str(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    idx = 1
    while True:
        candidate = parent / f"{stem}_{idx:03d}{suffix}"
        if not candidate.exists():
            return candidate
        idx += 1
