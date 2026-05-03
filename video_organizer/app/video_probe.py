import json
import logging
import subprocess
from pathlib import Path


def ffprobe_available() -> bool:
    try:
        r = subprocess.run(["ffprobe", "-version"], capture_output=True, text=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


def probe_video(path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", str(path)
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if r.returncode != 0:
            return {}
        data = json.loads(r.stdout or "{}")
        vstream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
        width = vstream.get("width")
        height = vstream.get("height")
        duration = float(vstream.get("duration") or data.get("format", {}).get("duration") or 0)
        codec = vstream.get("codec_name", "")
        r_frame = vstream.get("r_frame_rate", "0/0")
        fps = ""
        if "/" in r_frame:
            a, b = r_frame.split("/", 1)
            if b != "0":
                fps = f"{float(a)/float(b):.2f}"
        return {
            "resolution": f"{width}x{height}" if width and height else "",
            "duration": duration,
            "codec": codec,
            "fps": fps,
        }
    except Exception as e:
        logging.exception("ffprobe failed for %s: %s", path, e)
        return {}
