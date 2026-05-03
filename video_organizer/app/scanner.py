import logging
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot

from .config import SUPPORTED_EXTENSIONS
from .utils import ts_to_str
from .video_probe import probe_video


class ScannerWorker(QObject):
    progress = Signal(int, int)
    file_found = Signal(dict)
    finished = Signal()
    message = Signal(str)

    def __init__(self, root: str, use_probe: bool = True):
        super().__init__()
        self.root = Path(root)
        self._stop = False
        self.use_probe = use_probe

    def stop(self):
        self._stop = True

    @Slot()
    def run(self):
        try:
            files = [p for p in self.root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
            total = len(files)
            for i, p in enumerate(files, start=1):
                if self._stop:
                    break
                try:
                    st = p.stat()
                    meta = probe_video(p) if self.use_probe else {}
                    item = {
                        "name": p.name,
                        "path": str(p),
                        "folder": str(p.parent),
                        "ext": p.suffix.lower().lstrip("."),
                        "size_bytes": st.st_size,
                        "size_text": "",
                        "created": ts_to_str(st.st_ctime),
                        "modified": ts_to_str(st.st_mtime),
                        "resolution": meta.get("resolution", ""),
                        "duration": meta.get("duration", 0),
                        "codec": meta.get("codec", ""),
                        "fps": meta.get("fps", ""),
                        "suggested_category": "",
                        "duplicate": "",
                        "duplicate_type": "",
                        "reason": "",
                    }
                    self.file_found.emit(item)
                except Exception as e:
                    logging.exception("Error scanning file %s: %s", p, e)
                self.progress.emit(i, total)
        except Exception as e:
            logging.exception("Scanner crashed: %s", e)
            self.message.emit(str(e))
        finally:
            self.finished.emit()
