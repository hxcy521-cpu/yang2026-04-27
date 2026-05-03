import json
import shutil
from datetime import datetime
from pathlib import Path

from .config import UNDO_DIR
from .utils import unique_path


def decide_category(item: dict) -> tuple[str, str]:
    size = item.get("size_bytes", 0)
    ext = item.get("ext", "").lower()
    res = item.get("resolution", "")
    dur = float(item.get("duration") or 0)
    dup = item.get("duplicate") == "是"

    if dup:
        return "重复文件_待确认", "疑似/完全重复"
    if res == "5400x1800":
        return "超宽屏素材_5400x1800", "分辨率为5400x1800"
    if res == "3840x2160":
        return "4K素材", "分辨率为3840x2160"
    if res == "1920x1080":
        return "1080P素材", "分辨率为1920x1080"
    if ext == "mov":
        return "MOV源文件", "MOV格式"
    if ext == "mp4":
        return "MP4成品文件", "MP4格式"
    if size > 10 * 1024 ** 3:
        return "大文件_10GB以上", "文件大于10GB"
    if dur <= 15 and dur > 0:
        return "短循环素材", "时长<=15秒"
    return "其他视频", "默认分类"


def generate_plan(items: list[dict], base: str) -> list[dict]:
    base_path = Path(base)
    planned = []
    for item in items:
        cat, reason = decide_category(item)
        new_path = base_path / cat / item["name"]
        planned.append({
            "current_path": item["path"],
            "new_path": str(new_path),
            "reason": reason,
            "category": cat,
        })
        item["suggested_category"] = cat
        item["reason"] = reason
    return planned


def execute_plan(plan: list[dict]) -> Path:
    records = []
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    for p in plan:
        src = Path(p["current_path"])
        dst = unique_path(Path(p["new_path"]))
        dst.parent.mkdir(parents=True, exist_ok=True)
        size = src.stat().st_size if src.exists() else 0
        shutil.move(str(src), str(dst))
        records.append({
            "original_path": str(src),
            "new_path": str(dst),
            "time": now,
            "size_bytes": size,
            "reason": p["reason"],
        })
    log_file = UNDO_DIR / f"undo_{now}.json"
    with log_file.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    return log_file


def undo_last() -> str:
    logs = sorted(UNDO_DIR.glob("undo_*.json"))
    if not logs:
        return "没有可撤回记录"
    latest = logs[-1]
    with latest.open("r", encoding="utf-8") as f:
        records = json.load(f)
    for r in records:
        src = Path(r["new_path"])
        dst = Path(r["original_path"])
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
    return f"已撤回: {latest.name}"
