import logging
from collections import defaultdict
from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton, QProgressBar,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
)

from .duplicate_checker import mark_exact_duplicates, mark_suspected_duplicates
from .organizer import execute_plan, generate_plan, undo_last
from .report_exporter import export_csv, export_excel
from .scanner import ScannerWorker
from .utils import format_size
from .video_probe import ffprobe_available


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("视频素材整理工具")
        self.resize(1400, 820)
        self.folder = ""
        self.items = []
        self.plan = []
        self.scanner_thread = None
        self.worker = None
        self.has_ffprobe = ffprobe_available()
        self._init_ui()

    def _init_ui(self):
        root = QWidget(); self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        self.stats = QLabel("总数:0 | 总容量:0 MB")
        self.progress = QProgressBar()
        layout.addWidget(self.stats)
        layout.addWidget(self.progress)

        btns = QHBoxLayout()
        self.btn_select = QPushButton("选择文件夹")
        self.btn_scan = QPushButton("开始扫描")
        self.btn_stop = QPushButton("停止扫描")
        self.btn_export = QPushButton("导出报表")
        self.btn_plan = QPushButton("生成整理规划")
        self.btn_preview = QPushButton("预览整理结果")
        self.btn_exec = QPushButton("执行整理")
        self.btn_undo = QPushButton("撤回上一次整理")
        self.btn_hash = QPushButton("计算完整重复(Hash)")
        for b in [self.btn_select, self.btn_scan, self.btn_stop, self.btn_export, self.btn_plan, self.btn_preview, self.btn_exec, self.btn_undo, self.btn_hash]:
            btns.addWidget(b)
        layout.addLayout(btns)

        filters = QGridLayout()
        self.cb_ext = QComboBox(); self.cb_ext.addItems(["全部格式"])
        self.cb_res = QComboBox(); self.cb_res.addItems(["全部分辨率"])
        self.cb_size = QComboBox(); self.cb_size.addItems(["全部大小", ">1GB", ">5GB", ">10GB"])
        self.chk_dup = QCheckBox("只看重复")
        self.search = QLineEdit(); self.search.setPlaceholderText("搜索文件名关键词")
        filters.addWidget(QLabel("格式"), 0, 0); filters.addWidget(self.cb_ext, 0, 1)
        filters.addWidget(QLabel("分辨率"), 0, 2); filters.addWidget(self.cb_res, 0, 3)
        filters.addWidget(QLabel("大小"), 0, 4); filters.addWidget(self.cb_size, 0, 5)
        filters.addWidget(self.chk_dup, 0, 6); filters.addWidget(self.search, 0, 7)
        layout.addLayout(filters)

        self.table = QTableWidget(0, 14)
        self.table.setHorizontalHeaderLabels([
            "文件名", "完整路径", "文件夹", "后缀", "大小", "大小字节", "创建时间", "修改时间",
            "分辨率", "时长(秒)", "编码", "帧率", "建议分类", "是否疑似重复"
        ])
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        self.btn_select.clicked.connect(self.select_folder)
        self.btn_scan.clicked.connect(self.start_scan)
        self.btn_stop.clicked.connect(self.stop_scan)
        self.btn_export.clicked.connect(self.export_report)
        self.btn_plan.clicked.connect(self.make_plan)
        self.btn_preview.clicked.connect(self.preview_plan)
        self.btn_exec.clicked.connect(self.run_plan)
        self.btn_undo.clicked.connect(self.undo)
        self.btn_hash.clicked.connect(self.calc_exact_dup)
        self.cb_ext.currentTextChanged.connect(self.apply_filters)
        self.cb_res.currentTextChanged.connect(self.apply_filters)
        self.cb_size.currentTextChanged.connect(self.apply_filters)
        self.chk_dup.stateChanged.connect(self.apply_filters)
        self.search.textChanged.connect(self.apply_filters)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder: self.folder = folder

    def start_scan(self):
        if not self.folder:
            QMessageBox.warning(self, "提示", "请先选择文件夹"); return
        self.items.clear(); self.table.setRowCount(0)
        self.progress.setValue(0)
        self.worker = ScannerWorker(self.folder, self.has_ffprobe)
        self.scanner_thread = QThread()
        self.worker.moveToThread(self.scanner_thread)
        self.scanner_thread.started.connect(self.worker.run)
        self.worker.file_found.connect(self.on_file)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.finished.connect(self.scanner_thread.quit)
        self.scanner_thread.start()
        if not self.has_ffprobe:
            QMessageBox.information(self, "提示", "未检测到 ffprobe，将仅显示基础信息")

    def stop_scan(self):
        if self.worker: self.worker.stop()

    def on_file(self, item):
        item["size_text"] = format_size(item["size_bytes"])
        self.items.append(item)
        self.refresh_table()

    def on_progress(self, done, total):
        self.progress.setMaximum(max(1, total))
        self.progress.setValue(done)

    def on_finished(self):
        mark_suspected_duplicates(self.items)
        self.refresh_table(); self.refresh_stats(); self.refresh_filter_options()

    def refresh_filter_options(self):
        exts = sorted({i["ext"] for i in self.items}); reses = sorted({i["resolution"] for i in self.items if i["resolution"]})
        self.cb_ext.blockSignals(True); self.cb_res.blockSignals(True)
        self.cb_ext.clear(); self.cb_ext.addItem("全部格式"); self.cb_ext.addItems(exts)
        self.cb_res.clear(); self.cb_res.addItem("全部分辨率"); self.cb_res.addItems(reses)
        self.cb_ext.blockSignals(False); self.cb_res.blockSignals(False)

    def filter_items(self):
        items = self.items
        ext = self.cb_ext.currentText(); res = self.cb_res.currentText(); size = self.cb_size.currentText()
        kw = self.search.text().strip().lower(); only_dup = self.chk_dup.isChecked()
        out = []
        for i in items:
            if ext != "全部格式" and i["ext"] != ext: continue
            if res != "全部分辨率" and i["resolution"] != res: continue
            if size == ">1GB" and i["size_bytes"] <= 1024**3: continue
            if size == ">5GB" and i["size_bytes"] <= 5*1024**3: continue
            if size == ">10GB" and i["size_bytes"] <= 10*1024**3: continue
            if only_dup and i.get("duplicate") != "是": continue
            if kw and kw not in i["name"].lower(): continue
            out.append(i)
        return out

    def apply_filters(self): self.refresh_table()

    def refresh_table(self):
        rows = self.filter_items() if self.items else []
        self.table.setRowCount(len(rows))
        for r, i in enumerate(rows):
            vals = [i["name"], i["path"], i["folder"], i["ext"], i["size_text"], str(i["size_bytes"]), i["created"], i["modified"],
                    i["resolution"], f"{float(i.get('duration') or 0):.2f}", i["codec"], i["fps"], i.get("suggested_category", ""), i.get("duplicate_type", i.get("duplicate", ""))]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if c == 5: it.setData(Qt.EditRole, int(i["size_bytes"]))
                self.table.setItem(r, c, it)

    def refresh_stats(self):
        total = len(self.items); total_size = sum(i["size_bytes"] for i in self.items)
        mov = [i for i in self.items if i["ext"] == "mov"]
        mp4 = [i for i in self.items if i["ext"] == "mp4"]
        other = [i for i in self.items if i["ext"] not in {"mov", "mp4"}]
        dup_size = sum(i["size_bytes"] for i in self.items if i.get("duplicate") == "是")
        max_file = max(self.items, key=lambda x: x["size_bytes"], default={"name": "-", "size_bytes": 0})
        txt = (f"视频总数量:{total} | 视频总容量:{format_size(total_size)} | 最大文件:{max_file['name']}({format_size(max_file['size_bytes'])}) | "
               f"MOV:{len(mov)}个/{format_size(sum(i['size_bytes'] for i in mov))} | "
               f"MP4:{len(mp4)}个/{format_size(sum(i['size_bytes'] for i in mp4))} | "
               f"其他:{len(other)}个/{format_size(sum(i['size_bytes'] for i in other))} | "
               f"疑似重复容量:{format_size(dup_size)}")
        self.stats.setText(txt)

    def calc_exact_dup(self):
        mark_exact_duplicates(self.items, "md5")
        self.refresh_table(); self.refresh_stats()
        QMessageBox.information(self, "完成", "已完成完整重复检测")

    def make_plan(self):
        if not self.items: return
        self.plan = generate_plan(self.items, self.folder)
        self.refresh_table(); QMessageBox.information(self, "完成", "已生成整理规划")

    def preview_plan(self):
        if not self.plan:
            QMessageBox.information(self, "提示", "请先生成整理规划")
            return
        lines = [f"{p['current_path']} -> {p['new_path']} ({p['reason']})" for p in self.plan[:100]]
        QMessageBox.information(self, "预览(最多100条)", "\n".join(lines))

    def run_plan(self):
        if not self.plan: return
        ok = QMessageBox.question(self, "确认", "确认执行整理？")
        if ok != QMessageBox.StandardButton.Yes: return
        try:
            logf = execute_plan(self.plan)
            QMessageBox.information(self, "完成", f"整理完成，日志: {logf}")
        except Exception as e:
            logging.exception("execute failed: %s", e)
            QMessageBox.critical(self, "错误", str(e))

    def undo(self):
        msg = undo_last()
        QMessageBox.information(self, "撤回", msg)

    def export_report(self):
        if not self.items: return
        path, _ = QFileDialog.getSaveFileName(self, "导出报表", "video_report.csv", "CSV Files (*.csv);;Excel Files (*.xlsx)")
        if not path: return
        if path.lower().endswith(".xlsx"):
            export_excel(self.items, path)
        else:
            if not path.lower().endswith(".csv"): path += ".csv"
            export_csv(self.items, path)
        QMessageBox.information(self, "完成", "导出成功")
