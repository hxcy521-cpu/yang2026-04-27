import csv
import json
import os
import re
import shutil
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from pypinyin import lazy_pinyin


class RenameApp:
    """批量重命名为拼音的主应用。"""

    PINYIN_MODE_LABELS = {
        "full_lower": "完整拼音小写：yinxiangshijie",
        "full_upper": "完整拼音大写：YINXIANGSHIJIE",
        "full_title": "拼音首字母大写：YinXiangShiJie",
        "abbr_upper": "首字母缩写大写：YXSJ",
        "abbr_lower": "首字母缩写小写：yxsj",
    }
    PINYIN_LABEL_TO_KEY = {v: k for k, v in PINYIN_MODE_LABELS.items()}
    SEP_LABELS = {"": "无", "_": "下划线 _", "-": "中划线 -", " ": "空格"}
    SEP_LABEL_TO_KEY = {v: k for k, v in SEP_LABELS.items()}
    CONFLICT_LABELS = {"auto_index": "自动加序号", "skip": "跳过冲突项", "forbid": "禁止覆盖"}
    CONFLICT_LABEL_TO_KEY = {v: k for k, v in CONFLICT_LABELS.items()}

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("D3_TOOL - 批量拼音重命名工具")
        self.root.geometry("1460x900")
        self.root.configure(bg="#F5F7FB")

        self.mode = ""
        self.mode_text = tk.StringVar(value="当前模式：未选择")
        self.selected_path = tk.StringVar(value="请选择文件夹或文件开始操作")
        self.rule_preview_var = tk.StringVar()
        self.summary_var = tk.StringVar(value="扫描结果：等待扫描")

        self.rename_files_var = tk.BooleanVar(value=True)
        self.rename_folders_var = tk.BooleanVar(value=True)

        self.pinyin_mode_var = tk.StringVar(value="full_title")
        self.separator_var = tk.StringVar(value="")

        self.add_date_suffix_var = tk.BooleanVar(value=False)
        self.date_suffix_var = tk.StringVar(value=datetime.now().strftime("%m%d"))
        self.add_version_suffix_var = tk.BooleanVar(value=False)
        self.version_suffix_var = tk.StringVar(value="1")

        self.selected_files: list[str] = []
        self.preview_items: list[dict] = []
        self.last_rename_csv = os.path.join(os.getcwd(), "rename_log.csv")

        self.conflict_strategy_var = tk.StringVar(value="auto_index")

        self.config_file = os.path.join(os.getcwd(), "app_config.json")
        self.config_data = self._load_config()

        self.logo_img = None
        self._build_ui()
        self._init_last_path()
        self._update_rule_preview()

    def _build_ui(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Card.TLabelframe", background="#FFFFFF", bordercolor="#D9DEE8", borderwidth=1)
        style.configure("Card.TLabelframe.Label", background="#FFFFFF", foreground="#0F172A", font=("Microsoft YaHei UI", 11, "bold"))

        title_frame = tk.Frame(self.root, bg="#FFFFFF", padx=16, pady=12)
        title_frame.pack(fill=tk.X, padx=8, pady=(8, 6))
        tk.Label(title_frame, text="🪶  D3_TOOL 批量拼音重命名工具", bg="#FFFFFF", fg="#111827", font=("Microsoft YaHei UI", 20, "bold")).pack(side=tk.LEFT)
        tk.Label(title_frame, text="支持文件 / 文件夹中文转拼音、日期后缀、版本号、预览导出", bg="#FFFFFF", fg="#6B7280", font=("Microsoft YaHei UI", 12)).pack(side=tk.LEFT, padx=18)
        tk.Label(title_frame, text="By: 印象视界_程阳", bg="#FFFFFF", fg="#111827", font=("Microsoft YaHei UI", 14, "bold")).pack(side=tk.RIGHT)

        body = tk.Frame(self.root, bg="#F5F7FB")
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        top_grid = tk.Frame(body, bg="#F5F7FB")
        top_grid.pack(fill=tk.X)

        step1 = ttk.LabelFrame(top_grid, text="1  选择对象", style="Card.TLabelframe", padding=14)
        step2 = ttk.LabelFrame(top_grid, text="2  设置命名规则", style="Card.TLabelframe", padding=14)
        step3 = ttk.LabelFrame(top_grid, text="3  后缀选项", style="Card.TLabelframe", padding=14)
        step1.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        step2.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
        step3.grid(row=0, column=2, sticky="nsew")
        top_grid.grid_columnconfigure(0, weight=2)
        top_grid.grid_columnconfigure(1, weight=4)
        top_grid.grid_columnconfigure(2, weight=2)

        tk.Button(step1, text="📁 选择文件夹", command=self.choose_folder, bg="#FFFFFF", fg="#0F172A", relief=tk.GROOVE, font=("Microsoft YaHei UI", 14, "bold"), padx=16, pady=10).pack(side=tk.LEFT)
        tk.Button(step1, text="📄 选择文件", command=self.choose_files, bg="#FFFFFF", fg="#0F172A", relief=tk.GROOVE, font=("Microsoft YaHei UI", 14, "bold"), padx=16, pady=10).pack(side=tk.LEFT, padx=10)
        self.mode_label = tk.Label(step1, textvariable=self.mode_text, bg="#FFFFFF", fg="#DC2626", font=("Microsoft YaHei UI", 14, "bold"))
        self.mode_label.pack(anchor="w", pady=(16, 2))
        tk.Label(step1, textvariable=self.selected_path, bg="#FFFFFF", fg="#64748B", font=("Microsoft YaHei UI", 12)).pack(anchor="w")

        tk.Label(step2, text="拼音模式", bg="#FFFFFF", fg="#0F172A", font=("Microsoft YaHei UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        self.pinyin_cb = ttk.Combobox(step2, state="readonly", values=list(self.PINYIN_LABEL_TO_KEY.keys()), width=34, font=("Microsoft YaHei UI", 12))
        self.pinyin_cb.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(4, 10))
        self.pinyin_cb.set(self.PINYIN_MODE_LABELS["full_title"])
        self.pinyin_cb.bind("<<ComboboxSelected>>", self._on_rule_change)

        tk.Label(step2, text="分隔符", bg="#FFFFFF", fg="#0F172A", font=("Microsoft YaHei UI", 12, "bold")).grid(row=0, column=1, sticky="w")
        self.sep_cb = ttk.Combobox(step2, state="readonly", values=list(self.SEP_LABEL_TO_KEY.keys()), width=20, font=("Microsoft YaHei UI", 12))
        self.sep_cb.grid(row=1, column=1, sticky="ew", pady=(4, 10))
        self.sep_cb.set(self.SEP_LABELS[""])
        self.sep_cb.bind("<<ComboboxSelected>>", self._on_rule_change)

        self.rule_preview_var = tk.StringVar()
        tk.Label(step2, textvariable=self.rule_preview_var, bg="#EEF5FF", fg="#1D4ED8", font=("Microsoft YaHei UI", 13, "bold"), padx=8, pady=8, anchor="w").grid(row=2, column=0, columnspan=2, sticky="ew")
        step2.grid_columnconfigure(0, weight=1)
        step2.grid_columnconfigure(1, weight=1)

        ttk.Checkbutton(step3, text="添加日期后缀", variable=self.add_date_suffix_var, command=self._update_rule_preview).grid(row=0, column=0, sticky="w")
        ttk.Entry(step3, textvariable=self.date_suffix_var, width=8).grid(row=0, column=1, padx=6)
        tk.Label(step3, text="格式: MMDD", bg="#FFFFFF", fg="#64748B", font=("Microsoft YaHei UI", 11)).grid(row=0, column=2, sticky="w")

        ttk.Checkbutton(step3, text="添加版本后缀", variable=self.add_version_suffix_var, command=self._update_rule_preview).grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Combobox(step3, textvariable=self.version_suffix_var, width=6, state="readonly", values=[str(i) for i in range(1, 11)]).grid(row=1, column=1, padx=6, pady=(10, 0))
        tk.Label(step3, text="格式: V1-V10", bg="#FFFFFF", fg="#64748B", font=("Microsoft YaHei UI", 11)).grid(row=1, column=2, sticky="w", pady=(10, 0))

        tk.Label(step3, text="冲突处理", bg="#FFFFFF", fg="#0F172A", font=("Microsoft YaHei UI", 12, "bold")).grid(row=2, column=0, columnspan=3, sticky="w", pady=(18, 4))
        self.conflict_cb = ttk.Combobox(step3, state="readonly", values=list(self.CONFLICT_LABEL_TO_KEY.keys()), width=24, font=("Microsoft YaHei UI", 12))
        self.conflict_cb.grid(row=3, column=0, columnspan=3, sticky="ew")
        self.conflict_cb.set(self.CONFLICT_LABELS["auto_index"])
        self.conflict_cb.bind("<<ComboboxSelected>>", self._on_conflict_change)

        step4 = ttk.LabelFrame(body, text="4  执行操作", style="Card.TLabelframe", padding=14)
        step4.pack(fill=tk.X, pady=(10, 8))
        tk.Button(step4, text="🔍 扫描预览", command=self.scan_preview, bg="#1663D6", fg="#FFFFFF", relief=tk.FLAT, font=("Microsoft YaHei UI", 17, "bold"), padx=20, pady=12).pack(side=tk.LEFT)
        self.rename_btn = tk.Button(step4, text="▶ 开始重命名（0）", command=self.rename_all, state=tk.DISABLED, bg="#C9CDD3", fg="#7A7F87", relief=tk.FLAT, font=("Microsoft YaHei UI", 17, "bold"), padx=20, pady=12)
        self.rename_btn.pack(side=tk.LEFT, padx=12)
        tk.Button(step4, text="↻ 撤回上次重命名", command=self.undo_last_rename, bg="#F59E0B", fg="#FFFFFF", relief=tk.FLAT, font=("Microsoft YaHei UI", 16, "bold"), padx=16, pady=12).pack(side=tk.LEFT, padx=8)
        ttk.Button(step4, text="导出预览CSV", command=self.export_preview_csv).pack(side=tk.LEFT, padx=8)
        tk.Button(step4, text="🧹 清空列表", command=self._clear_preview, bg="#7B8698", fg="#FFFFFF", relief=tk.FLAT, font=("Microsoft YaHei UI", 15, "bold"), padx=18, pady=12).pack(side=tk.LEFT, padx=8)
        ttk.Checkbutton(step4, text="重命名文件", variable=self.rename_files_var, command=self._on_filter_change).pack(side=tk.LEFT, padx=(14, 2))
        ttk.Checkbutton(step4, text="重命名文件夹", variable=self.rename_folders_var, command=self._on_filter_change).pack(side=tk.LEFT, padx=2)

        tk.Label(body, textvariable=self.summary_var, bg="#F5F7FB", fg="#0F172A", font=("Microsoft YaHei UI", 13, "bold")).pack(fill=tk.X, pady=(0, 6))

        preview_frame = ttk.LabelFrame(body, text="预览列表", style="Card.TLabelframe", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        columns = ("idx", "type", "old_name", "new_name", "old_path", "status")
        self.tree = ttk.Treeview(preview_frame, columns=columns, show="headings", height=12)
        headers = ["序号", "类型", "原名称", "新名称", "所在路径", "状态"]
        for c, h in zip(columns, headers):
            self.tree.heading(c, text=h)
        self.tree.column("idx", width=56, anchor=tk.CENTER)
        self.tree.column("type", width=70, anchor=tk.CENTER)
        self.tree.column("old_name", width=240)
        self.tree.column("new_name", width=360)
        self.tree.column("old_path", width=520)
        self.tree.column("status", width=180, anchor=tk.CENTER)
        yscroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        status_frame = ttk.Frame(body, padding=(0, 0, 0, 4))
        status_frame.pack(fill=tk.X)
        self.progress = ttk.Progressbar(status_frame, orient=tk.HORIZONTAL, mode="determinate")
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.status_var = tk.StringVar(value="状态：就绪")
        ttk.Label(status_frame, textvariable=self.status_var, width=36).pack(side=tk.LEFT, padx=(8, 0))

        log_frame = ttk.LabelFrame(body, text="日志输出", style="Card.TLabelframe", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(log_frame, height=5)
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_rule_change(self, _event=None) -> None:
        self.pinyin_mode_var.set(self.PINYIN_LABEL_TO_KEY.get(self.pinyin_cb.get(), "full_title"))
        self.separator_var.set(self.SEP_LABEL_TO_KEY.get(self.sep_cb.get(), ""))
        self._update_rule_preview()

    def _on_conflict_change(self, _event=None) -> None:
        self.conflict_strategy_var.set(self.CONFLICT_LABEL_TO_KEY.get(self.conflict_cb.get(), "auto_index"))

    def _update_rule_preview(self, *_args) -> None:
        sample = "印象视界素材"
        sample_ext = ".mov"
        new_base = normalize_to_pinyin(sample, self.pinyin_mode_var.get(), self.separator_var.get())
        new_base = self._apply_suffix(new_base or "unnamed")
        self.rule_preview_var.set(f"印象视界素材.mov → {new_base}{sample_ext}")

    def _init_last_path(self) -> None:
        last_mode = self.config_data.get("last_mode", "")
        last_folder = self.config_data.get("last_folder", "")
        if last_mode == "folder" and last_folder and os.path.isdir(last_folder):
            self.mode = "folder"
            self.mode_text.set("当前模式：文件夹模式")
            self.mode_label.config(fg="#16A34A")
            self.selected_path.set(f"已选文件夹：{last_folder}")
            self.log(f"已恢复上次路径：{last_folder}")

    def _load_config(self) -> dict:
        if not os.path.exists(self.config_file):
            return {}
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_config(self) -> None:
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"保存配置失败：{e}")

    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def choose_folder(self) -> None:
        initial_dir = self.config_data.get("last_folder", "")
        path = filedialog.askdirectory(title="请选择要处理的文件夹", initialdir=initial_dir)
        if path:
            self.mode = "folder"
            self.selected_files = []
            self.mode_text.set("当前模式：文件夹模式")
            self.mode_label.config(fg="#16A34A")
            self.selected_path.set(f"已选文件夹：{path}")
            self.log(f"已切换为文件夹模式：{path}")
            self.config_data["last_mode"] = "folder"
            self.config_data["last_folder"] = path
            self._save_config()

    def choose_files(self) -> None:
        initial_dir = self.config_data.get("last_files_dir", self.config_data.get("last_folder", ""))
        paths = filedialog.askopenfilenames(title="请选择要处理的文件（可多选）", initialdir=initial_dir)
        if paths:
            self.mode = "files"
            self.selected_files = list(paths)
            self.mode_text.set("当前模式：文件模式")
            self.mode_label.config(fg="#16A34A")
            self.selected_path.set(f"已选文件数：{len(self.selected_files)}")
            self.log(f"已切换为文件模式，共选择 {len(self.selected_files)} 个文件")
            self.config_data["last_mode"] = "files"
            self.config_data["last_files_dir"] = os.path.dirname(self.selected_files[0])
            self._save_config()

    def _on_filter_change(self) -> None:
        if not self.rename_files_var.get() and not self.rename_folders_var.get():
            self.log("提示：当前两个勾选都未选中，将不会产生重命名计划。")

    def _validate_suffix_rules(self) -> bool:
        if self.add_date_suffix_var.get():
            date_text = self.date_suffix_var.get().strip()
            if (not date_text.isdigit()) or len(date_text) != 4:
                messagebox.showerror("错误", "日期尾缀必须是4位数字，例如 0502")
                return False
        if self.add_version_suffix_var.get():
            version_text = self.version_suffix_var.get().strip()
            if not version_text.isdigit() or not (1 <= int(version_text) <= 10):
                messagebox.showerror("错误", "版本号范围只能是 V1 到 V10")
                return False
        return True

    def _apply_suffix(self, base_name: str) -> str:
        new_name = base_name
        if self.add_date_suffix_var.get():
            new_name += f"_{self.date_suffix_var.get().strip()}"
        if self.add_version_suffix_var.get():
            new_name += f"_V{self.version_suffix_var.get().strip()}"
        return new_name

    def convert_name(self, name: str, is_file: bool) -> str:
        if is_file:
            stem, ext = split_filename(name)
            new_stem = normalize_to_pinyin(stem, self.pinyin_mode_var.get(), self.separator_var.get())
            new_stem = self._apply_suffix(new_stem or "unnamed")
            return f"{new_stem}{ext}"
        new_name = normalize_to_pinyin(name, self.pinyin_mode_var.get(), self.separator_var.get()) or "unnamed_folder"
        return self._apply_suffix(new_name)

    def _clear_preview(self) -> None:
        self.preview_items.clear()
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.rename_btn.config(state=tk.DISABLED, bg="#C9CDD3", fg="#7A7F87", text="开始重命名（0）")
        self.progress["value"] = 0
        self.status_var.set("状态：就绪")
        self.summary_var.set("扫描结果：等待扫描")

    def scan_preview(self) -> None:
        self._clear_preview()
        if not self._validate_suffix_rules():
            return
        if self.mode == "folder":
            self._scan_folder_mode()
        elif self.mode == "files":
            self._scan_files_mode()
        else:
            messagebox.showwarning("提示", "请先选择文件或文件夹。")
            return

        file_count = sum(1 for x in self.preview_items if x["type"] == "文件")
        folder_count = sum(1 for x in self.preview_items if x["type"] == "文件夹")
        ready_count = sum(1 for x in self.preview_items if x["status"] == "待重命名")
        conflict_count = sum(1 for x in self.preview_items if "冲突" in x["status"])
        error_count = sum(1 for x in self.preview_items if "错误" in x["status"] or "不存在" in x["status"])

        for idx, item in enumerate(self.preview_items, start=1):
            self.tree.insert("", tk.END, values=(idx, item["type"], item["old_name"], item["new_name"], os.path.dirname(item["old_path"]), item["status"]))

        self.summary_var.set(f"扫描结果：共 {len(self.preview_items)} 个项目（文件 {file_count} 个，文件夹 {folder_count} 个）  |  可重命名：{ready_count} 个（绿色）  |  冲突跳过：{conflict_count} 个（橙色）  |  错误：{error_count} 个（红色）")
        self.log(f"扫描完成，共 {len(self.preview_items)} 个项目（文件 {file_count} 个，文件夹 {folder_count} 个）")
        self.rename_btn.config(
            state=(tk.NORMAL if ready_count > 0 else tk.DISABLED),
            bg=("#D92D20" if ready_count > 0 else "#C9CDD3"),
            fg=("#FFFFFF" if ready_count > 0 else "#7A7F87"),
            text=f"开始重命名（{ready_count})"
        )
        self.status_var.set(f"状态：预览完成 {len(self.preview_items)} 条")

    def _scan_folder_mode(self) -> None:
        root_dir = self.selected_path.get().replace("已选文件夹：", "", 1).strip()
        if not root_dir or not os.path.isdir(root_dir):
            messagebox.showerror("错误", "请选择有效文件夹。")
            return
        used_targets = set()
        if self.rename_files_var.get():
            for current_root, _dirs, files in os.walk(root_dir):
                for filename in files:
                    old_path = os.path.join(current_root, filename)
                    new_name = self.convert_name(filename, is_file=True)
                    if new_name == filename:
                        continue
                    target = os.path.join(current_root, new_name)
                    status, new_path = self._resolve_conflict(target, used_targets)
                    used_targets.add(new_path)
                    self.preview_items.append(make_preview_item(old_path, new_path, "文件", status))
        if self.rename_folders_var.get():
            dir_paths = []
            for current_root, dirs, _files in os.walk(root_dir):
                for d in dirs:
                    dir_paths.append(os.path.join(current_root, d))
            dir_paths.sort(key=lambda p: p.count(os.sep), reverse=True)
            for old_dir in dir_paths:
                old_name = os.path.basename(old_dir)
                parent = os.path.dirname(old_dir)
                new_name = self.convert_name(old_name, is_file=False)
                if new_name == old_name:
                    continue
                target = os.path.join(parent, new_name)
                status, new_path = self._resolve_conflict(target, used_targets)
                used_targets.add(new_path)
                self.preview_items.append(make_preview_item(old_dir, new_path, "文件夹", status))

    def _resolve_conflict(self, target: str, used_targets: set[str]) -> tuple[str, str]:
        if os.path.exists(target) or target in used_targets:
            if self.conflict_strategy_var.get() in {"skip", "forbid"}:
                return "冲突，已跳过", target
            return "待重命名", unique_target_path(target, used_targets)
        return "待重命名", target

    def _scan_files_mode(self) -> None:
        if not self.selected_files:
            messagebox.showwarning("提示", "请先选择一个或多个文件。")
            return
        if not self.rename_files_var.get():
            self.log("当前已关闭重命名文件，文件模式下将无任务。")
            return
        used_targets = set()
        for old_path in self.selected_files:
            if not os.path.isfile(old_path):
                self.preview_items.append({"old_path": old_path, "old_name": os.path.basename(old_path), "new_name": "-", "new_path": old_path, "type": "文件", "status": "源文件不存在"})
                continue
            old_name = os.path.basename(old_path)
            parent = os.path.dirname(old_path)
            new_name = self.convert_name(old_name, is_file=True)
            if new_name == old_name:
                self.preview_items.append({"old_path": old_path, "old_name": old_name, "new_name": new_name, "new_path": old_path, "type": "文件", "status": "无需重命名"})
                continue
            target = os.path.join(parent, new_name)
            status, new_path = self._resolve_conflict(target, used_targets)
            used_targets.add(new_path)
            self.preview_items.append(make_preview_item(old_path, new_path, "文件", status))

    def export_preview_csv(self) -> None:
        if not self.preview_items:
            messagebox.showinfo("提示", "当前没有可导出的预览数据，请先扫描预览。")
            return
        default_dir = self.config_data.get("last_folder", os.getcwd())
        save_path = filedialog.asksaveasfilename(title="保存预览CSV", initialdir=default_dir, defaultextension=".csv", filetypes=[("CSV 文件", "*.csv")], initialfile=f"preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        if not save_path:
            return
        try:
            with open(save_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["原路径", "原名称", "新名称", "状态", "类型", "新路径"])
                for item in self.preview_items:
                    writer.writerow([item["old_path"], item["old_name"], item["new_name"], item["status"], item["type"], item["new_path"]])
            self.log(f"已导出预览CSV：{save_path}")
            messagebox.showinfo("完成", f"导出成功：\n{save_path}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败：{e}")

    def rename_all(self) -> None:
        if not self.preview_items:
            messagebox.showinfo("提示", "请先点击扫描预览确认结果后再重命名。")
            return
        plans = [x for x in self.preview_items if x["status"] == "待重命名"]
        confirm = messagebox.askyesno("确认重命名", f"即将重命名 {len(plans)} 个文件/文件夹，是否继续？")
        if not confirm:
            self.log("用户取消重命名。")
            return
        log_file = self._get_log_path()
        file_items = [x for x in plans if x["type"] == "文件"]
        folder_items = [x for x in plans if x["type"] == "文件夹"]
        folder_items.sort(key=lambda x: x["old_path"].count(os.sep), reverse=True)
        ordered_plans = file_items + folder_items
        done = failed = skipped = 0
        total = len(ordered_plans)
        self.progress["maximum"] = max(total, 1)
        self.progress["value"] = 0
        with open(log_file, "a", encoding="utf-8") as f, open(self.last_rename_csv, "w", newline="", encoding="utf-8-sig") as csv_f:
            csv_writer = csv.writer(csv_f)
            csv_writer.writerow(["原路径", "新路径", "原名称", "新名称", "操作时间"])
            for idx, item in enumerate(ordered_plans, start=1):
                self.progress["value"] = idx
                self.status_var.set(f"状态：正在重命名 {idx}/{total}")
                self.root.update_idletasks()
                old_path = item["old_path"]
                real_target = unique_target_path(item["new_path"])
                if not os.path.exists(old_path):
                    skipped += 1
                    continue
                try:
                    shutil.move(old_path, real_target)
                    done += 1
                    csv_writer.writerow([old_path, real_target, os.path.basename(old_path), os.path.basename(real_target), datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                except Exception as e:
                    failed += 1
                    f.write(f"失败：{old_path}->{real_target} {e}\n")
        self.status_var.set(f"状态：完成 成功{done} 跳过{skipped} 失败{failed}")
        self.log(f"重命名完成：成功 {done}，跳过 {skipped}，失败 {failed}。日志：{log_file}")
        messagebox.showinfo("完成", f"重命名完成\n成功：{done}\n跳过：{skipped}\n失败：{failed}\n日志：{log_file}")

    def undo_last_rename(self) -> None:
        if not os.path.exists(self.last_rename_csv):
            messagebox.showinfo("提示", "未找到可撤回记录。")
            return
        success = failed = skipped = 0
        with open(self.last_rename_csv, "r", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        for row in reversed(rows):
            old_path, new_path = row.get("原路径", ""), row.get("新路径", "")
            if not old_path or not new_path:
                continue
            if os.path.exists(old_path):
                skipped += 1
                continue
            if not os.path.exists(new_path):
                failed += 1
                continue
            try:
                shutil.move(new_path, old_path)
                success += 1
            except Exception:
                failed += 1
        self.log(f"撤回完成：成功 {success}，失败 {failed}，跳过 {skipped}")
        messagebox.showinfo("撤回完成", f"撤回完成：成功 {success}，失败 {failed}，跳过 {skipped}")

    def _get_log_path(self) -> str:
        if self.mode == "folder":
            root_dir = self.selected_path.get().replace("已选文件夹：", "", 1).strip()
            return os.path.join(root_dir, "rename_log.txt")
        first_dir = os.path.dirname(self.selected_files[0]) if self.selected_files else os.getcwd()
        return os.path.join(first_dir, "rename_log.txt")


def split_filename(filename: str):
    if filename.startswith(".") and filename.count(".") == 1:
        return filename, ""
    return os.path.splitext(filename)


def normalize_to_pinyin(text: str, pinyin_mode: str = "full_lower", sep: str = "") -> str:
    tokens = []
    for ch in text:
        if re.match(r"[一-鿿]", ch):
            py = lazy_pinyin(ch)[0]
            if pinyin_mode == "full_upper":
                tokens.append(py.upper())
            elif pinyin_mode == "full_title":
                tokens.append(py[:1].upper() + py[1:].lower())
            elif pinyin_mode in {"abbr_lower", "abbr_upper"}:
                letter = py[:1].lower()
                tokens.append(letter.upper() if pinyin_mode == "abbr_upper" else letter)
            else:
                tokens.append(py.lower())
        elif re.match(r"[A-Za-z0-9]", ch):
            tokens.append(ch)
        else:
            tokens.append("_")
    text_out = sep.join(tokens) if sep else "".join(tokens)
    if sep:
        text_out = text_out.replace(f"{sep}_{sep}", sep)
    text_out = re.sub(r"_+", "_", text_out).strip("_")
    return text_out


def unique_target_path(path: str, reserved: set | None = None) -> str:
    reserved = reserved or set()
    folder = os.path.dirname(path)
    name = os.path.basename(path)
    stem, ext = os.path.splitext(name)
    candidate = path
    idx = 1
    while os.path.exists(candidate) or candidate in reserved:
        candidate = os.path.join(folder, f"{stem}_{idx:03d}{ext}")
        idx += 1
    return candidate


def make_preview_item(old_path: str, new_path: str, item_type: str, status: str = "待重命名") -> dict:
    return {
        "old_path": old_path,
        "old_name": os.path.basename(old_path),
        "new_name": os.path.basename(new_path),
        "new_path": new_path,
        "type": item_type,
        "status": status,
    }


if __name__ == "__main__":
    root = tk.Tk()
    app = RenameApp(root)
    root.mainloop()
