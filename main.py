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

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("D3_TOOL - 批量拼音重命名工具")
        self.root.geometry("1180x760")

        # 当前模式：folder 或 files
        self.mode = ""
        self.mode_text = tk.StringVar(value="当前模式：未选择")
        self.selected_path = tk.StringVar(value="")

        # 仅重命名文件/仅重命名文件夹勾选
        self.rename_files_var = tk.BooleanVar(value=True)
        self.rename_folders_var = tk.BooleanVar(value=True)

        # 第一阶段：拼音规则
        self.pinyin_mode_var = tk.StringVar(value="full_lower")
        self.separator_var = tk.StringVar(value="")

        # 第二阶段：文件名尾缀规则
        self.add_date_suffix_var = tk.BooleanVar(value=False)
        self.date_suffix_var = tk.StringVar(value=datetime.now().strftime("%m%d"))
        self.add_version_suffix_var = tk.BooleanVar(value=False)
        self.version_suffix_var = tk.StringVar(value="1")

        # 文件模式时保存用户选择的文件
        self.selected_files: list[str] = []

        # 预览项格式：dict(old_path, old_name, new_name, new_path, type, status)
        self.preview_items: list[dict] = []

        # 程序配置（记住上次路径）
        self.config_file = os.path.join(os.getcwd(), "app_config.json")
        self.config_data = self._load_config()

        self.logo_img = None
        self._build_ui()
        self._init_last_path()

    def _build_ui(self) -> None:
        """构建图形界面。"""
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)

        ttk.Button(top_frame, text="选择文件夹", command=self.choose_folder).pack(side=tk.LEFT)
        ttk.Button(top_frame, text="选择文件", command=self.choose_files).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(top_frame, textvariable=self.mode_text).pack(side=tk.LEFT, padx=(18, 0))
        ttk.Label(top_frame, text="By:印象视界_程阳", foreground="#2f4f4f").pack(side=tk.RIGHT)

        # LOGO：如果项目目录有 logo.png，将在界面右上角显示
        self._load_logo(top_frame)

        info_frame = ttk.Frame(self.root, padding=(10, 0, 10, 6))
        info_frame.pack(fill=tk.X)
        ttk.Label(info_frame, textvariable=self.selected_path, width=140).pack(side=tk.LEFT)

        action_frame = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        action_frame.pack(fill=tk.X)
        ttk.Button(action_frame, text="扫描预览", command=self.scan_preview).pack(side=tk.LEFT)
        ttk.Button(action_frame, text="开始重命名", command=self.rename_all).pack(side=tk.LEFT, padx=10)
        ttk.Button(action_frame, text="导出预览CSV", command=self.export_preview_csv).pack(side=tk.LEFT, padx=10)

        ttk.Checkbutton(
            action_frame,
            text="仅重命名文件",
            variable=self.rename_files_var,
            command=self._on_filter_change,
        ).pack(side=tk.LEFT, padx=(20, 5))
        ttk.Checkbutton(
            action_frame,
            text="仅重命名文件夹",
            variable=self.rename_folders_var,
            command=self._on_filter_change,
        ).pack(side=tk.LEFT)


        # 第一阶段：拼音规则区
        rule_frame = ttk.LabelFrame(self.root, text="拼音转换规则", padding=10)
        rule_frame.pack(fill=tk.X, padx=10, pady=(0, 6))

        ttk.Label(rule_frame, text="拼音模式：").pack(side=tk.LEFT)
        ttk.Combobox(
            rule_frame,
            textvariable=self.pinyin_mode_var,
            state="readonly",
            width=22,
            values=[
                "full_lower",
                "full_upper",
                "full_title",
                "abbr_lower",
                "abbr_upper",
            ],
        ).pack(side=tk.LEFT, padx=(0, 12))

        ttk.Label(rule_frame, text="分隔符：").pack(side=tk.LEFT)
        ttk.Combobox(
            rule_frame,
            textvariable=self.separator_var,
            state="readonly",
            width=10,
            values=["", "_", "-", " "],
        ).pack(side=tk.LEFT)

        suffix_frame = ttk.LabelFrame(self.root, text="文件名尾缀设置", padding=10)
        suffix_frame.pack(fill=tk.X, padx=10, pady=(0, 6))

        ttk.Checkbutton(suffix_frame, text="添加日期尾缀", variable=self.add_date_suffix_var).pack(side=tk.LEFT)
        ttk.Label(suffix_frame, text="日期(MMDD)：").pack(side=tk.LEFT, padx=(8, 2))
        ttk.Entry(suffix_frame, textvariable=self.date_suffix_var, width=8).pack(side=tk.LEFT, padx=(0, 12))

        ttk.Checkbutton(suffix_frame, text="添加版本尾缀", variable=self.add_version_suffix_var).pack(side=tk.LEFT)
        ttk.Label(suffix_frame, text="版本(V1-V10)：").pack(side=tk.LEFT, padx=(8, 2))
        ttk.Combobox(suffix_frame, textvariable=self.version_suffix_var, width=6, state="readonly",
                     values=[str(i) for i in range(1, 11)]).pack(side=tk.LEFT)

        preview_frame = ttk.LabelFrame(self.root, text="预览列表", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("old_path", "old_name", "new_name", "status")
        self.tree = ttk.Treeview(preview_frame, columns=columns, show="headings", height=16)
        self.tree.heading("old_path", text="原路径")
        self.tree.heading("old_name", text="原名称")
        self.tree.heading("new_name", text="新名称")
        self.tree.heading("status", text="状态")

        self.tree.column("old_path", width=530)
        self.tree.column("old_name", width=180)
        self.tree.column("new_name", width=240)
        self.tree.column("status", width=120, anchor=tk.CENTER)

        yscroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        log_frame = ttk.LabelFrame(self.root, text="日志输出", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.log_text = tk.Text(log_frame, height=10)
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _load_logo(self, parent: ttk.Frame) -> None:
        """加载并显示 LOGO（可选）。"""
        logo_path = os.path.join(os.getcwd(), "logo.png")
        if not os.path.exists(logo_path):
            return
        try:
            self.logo_img = tk.PhotoImage(file=logo_path)
            ttk.Label(parent, image=self.logo_img).pack(side=tk.RIGHT, padx=(10, 0))
            self.log("已加载 logo.png")
        except Exception:
            # 不因为 logo 加载失败影响主功能
            pass

    def _init_last_path(self) -> None:
        """初始化上次路径显示。"""
        last_mode = self.config_data.get("last_mode", "")
        last_folder = self.config_data.get("last_folder", "")

        if last_mode == "folder" and last_folder and os.path.isdir(last_folder):
            self.mode = "folder"
            self.mode_text.set("当前模式：文件夹模式")
            self.selected_path.set(f"已选文件夹：{last_folder}")
            self.log(f"已恢复上次路径：{last_folder}")

    def _load_config(self) -> dict:
        """读取本地配置。"""
        if not os.path.exists(self.config_file):
            return {}
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_config(self) -> None:
        """保存本地配置。"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"保存配置失败：{e}")

    def log(self, message: str) -> None:
        """输出日志到界面。"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def choose_folder(self) -> None:
        """选择文件夹模式。"""
        initial_dir = self.config_data.get("last_folder", "")
        path = filedialog.askdirectory(title="请选择要处理的文件夹", initialdir=initial_dir)
        if path:
            self.mode = "folder"
            self.selected_files = []
            self.mode_text.set("当前模式：文件夹模式")
            self.selected_path.set(f"已选文件夹：{path}")
            self.log(f"已切换为文件夹模式：{path}")
            self.config_data["last_mode"] = "folder"
            self.config_data["last_folder"] = path
            self._save_config()

    def choose_files(self) -> None:
        """选择文件模式，可多选文件。"""
        initial_dir = self.config_data.get("last_files_dir", self.config_data.get("last_folder", ""))
        paths = filedialog.askopenfilenames(title="请选择要处理的文件（可多选）", initialdir=initial_dir)
        if paths:
            self.mode = "files"
            self.selected_files = list(paths)
            self.mode_text.set("当前模式：文件模式")
            self.selected_path.set(f"已选文件数：{len(self.selected_files)}")
            self.log(f"已切换为文件模式，共选择 {len(self.selected_files)} 个文件")
            self.config_data["last_mode"] = "files"
            self.config_data["last_files_dir"] = os.path.dirname(self.selected_files[0])
            self._save_config()

    def _on_filter_change(self) -> None:
        """勾选变化时提示。"""
        if not self.rename_files_var.get() and not self.rename_folders_var.get():
            self.log("提示：当前两个勾选都未选中，将不会产生重命名计划。")

    def _validate_suffix_rules(self) -> bool:
        """校验日期/版本尾缀输入。"""
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
        """在文件名主体后添加日期/版本尾缀。"""
        new_name = base_name
        if self.add_date_suffix_var.get():
            new_name += f"_{self.date_suffix_var.get().strip()}"
        if self.add_version_suffix_var.get():
            new_name += f"_V{self.version_suffix_var.get().strip()}"
        return new_name

    def convert_name(self, name: str, is_file: bool) -> str:
        """将名称转换为拼音，不改变文件扩展名。"""
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

    def scan_preview(self) -> None:
        """扫描并生成预览，不会执行重命名。"""
        self._clear_preview()

        if not self._validate_suffix_rules():
            return

        if self.mode == "folder":
            self._scan_folder_mode()
        elif self.mode == "files":
            self._scan_files_mode()
        else:
            messagebox.showwarning("提示", "请先选择“文件夹”或“文件”模式。")
            return

        for item in self.preview_items:
            self.tree.insert(
                "", tk.END,
                values=(item["old_path"], item["old_name"], item["new_name"], item["status"])
            )

        self.log(f"扫描预览完成，共 {len(self.preview_items)} 条。")

    def _scan_folder_mode(self) -> None:
        root_dir = self.selected_path.get().replace("已选文件夹：", "", 1).strip()
        if not root_dir or not os.path.isdir(root_dir):
            messagebox.showerror("错误", "请选择有效文件夹。")
            return

        used_targets = set()

        # 先处理文件
        if self.rename_files_var.get():
            for current_root, _dirs, files in os.walk(root_dir):
                for filename in files:
                    old_path = os.path.join(current_root, filename)
                    new_name = self.convert_name(filename, is_file=True)
                    if new_name == filename:
                        continue
                    new_path = unique_target_path(os.path.join(current_root, new_name), used_targets)
                    used_targets.add(new_path)
                    self.preview_items.append(make_preview_item(old_path, new_path, "文件"))

        # 再收集文件夹（深->浅）
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
                new_path = unique_target_path(os.path.join(parent, new_name), used_targets)
                used_targets.add(new_path)
                self.preview_items.append(make_preview_item(old_dir, new_path, "文件夹"))

    def _scan_files_mode(self) -> None:
        if not self.selected_files:
            messagebox.showwarning("提示", "请先选择一个或多个文件。")
            return

        if not self.rename_files_var.get():
            self.log("当前已关闭“仅重命名文件”，文件模式下将无任务。")
            return

        used_targets = set()
        for old_path in self.selected_files:
            if not os.path.isfile(old_path):
                self.preview_items.append(
                    {
                        "old_path": old_path,
                        "old_name": os.path.basename(old_path),
                        "new_name": "-",
                        "new_path": old_path,
                        "type": "文件",
                        "status": "源文件不存在",
                    }
                )
                continue

            old_name = os.path.basename(old_path)
            parent = os.path.dirname(old_path)
            new_name = self.convert_name(old_name, is_file=True)

            if new_name == old_name:
                self.preview_items.append(
                    {
                        "old_path": old_path,
                        "old_name": old_name,
                        "new_name": new_name,
                        "new_path": old_path,
                        "type": "文件",
                        "status": "无需重命名",
                    }
                )
                continue

            new_path = unique_target_path(os.path.join(parent, new_name), used_targets)
            used_targets.add(new_path)
            self.preview_items.append(make_preview_item(old_path, new_path, "文件"))

    def export_preview_csv(self) -> None:
        """导出预览列表到 CSV。"""
        if not self.preview_items:
            messagebox.showinfo("提示", "当前没有可导出的预览数据，请先扫描预览。")
            return

        default_dir = self.config_data.get("last_folder", os.getcwd())
        save_path = filedialog.asksaveasfilename(
            title="保存预览CSV",
            initialdir=default_dir,
            defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv")],
            initialfile=f"preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
        if not save_path:
            return

        try:
            with open(save_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["原路径", "原名称", "新名称", "状态", "类型", "新路径"])
                for item in self.preview_items:
                    writer.writerow([
                        item["old_path"],
                        item["old_name"],
                        item["new_name"],
                        item["status"],
                        item["type"],
                        item["new_path"],
                    ])
            self.log(f"已导出预览CSV：{save_path}")
            messagebox.showinfo("完成", f"导出成功：\n{save_path}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败：{e}")

    def rename_all(self) -> None:
        """执行重命名（必须先预览），并二次确认。"""
        if not self.preview_items:
            messagebox.showinfo("提示", "请先点击“扫描预览”确认结果后再重命名。")
            return

        confirm = messagebox.askyesno("二次确认", "请确认已备份重要文件，是否继续？")
        if not confirm:
            self.log("用户取消重命名。")
            return

        log_file = self._get_log_path()
        plans = [x for x in self.preview_items if x["status"] == "待重命名"]

        # 文件夹重命名时需深->浅
        file_items = [x for x in plans if x["type"] == "文件"]
        folder_items = [x for x in plans if x["type"] == "文件夹"]
        folder_items.sort(key=lambda x: x["old_path"].count(os.sep), reverse=True)
        ordered_plans = file_items + folder_items

        done, failed = 0, 0
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n===== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 开始 =====\n")
            f.write(f"模式：{'文件夹模式' if self.mode == 'folder' else '文件模式'}\n")
            for item in ordered_plans:
                old_path = item["old_path"]
                preview_new_path = item["new_path"]
                item_type = item["type"]

                if not os.path.exists(old_path):
                    msg = f"跳过（源不存在）[{item_type}]：{old_path}"
                    self.log(msg)
                    f.write(msg + "\n")
                    failed += 1
                    continue

                real_target = unique_target_path(preview_new_path)
                if os.path.abspath(real_target) == os.path.abspath(old_path):
                    continue

                try:
                    shutil.move(old_path, real_target)
                    msg = f"成功[{item_type}]：{old_path} -> {real_target}"
                    self.log(msg)
                    f.write(msg + "\n")
                    done += 1
                except Exception as e:
                    msg = f"失败[{item_type}]：{old_path} -> {real_target}，原因：{e}"
                    self.log(msg)
                    f.write(msg + "\n")
                    failed += 1
            f.write(f"完成：成功 {done}，失败 {failed}\n")

        self.log(f"重命名完成：成功 {done}，失败 {failed}。日志：{log_file}")
        messagebox.showinfo("完成", f"重命名完成\n成功：{done}\n失败：{failed}\n日志：{log_file}")

    def _get_log_path(self) -> str:
        """根据模式决定日志文件位置。"""
        if self.mode == "folder":
            root_dir = self.selected_path.get().replace("已选文件夹：", "", 1).strip()
            return os.path.join(root_dir, "rename_log.txt")

        first_dir = os.path.dirname(self.selected_files[0]) if self.selected_files else os.getcwd()
        return os.path.join(first_dir, "rename_log.txt")


def split_filename(filename: str):
    """保留最后一个扩展名。"""
    if filename.startswith(".") and filename.count(".") == 1:
        return filename, ""
    return os.path.splitext(filename)


def normalize_to_pinyin(text: str, pinyin_mode: str = "full_lower", sep: str = "") -> str:
    """中文转拼音并应用模式、分隔符。"""
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
                if pinyin_mode == "abbr_upper":
                    letter = letter.upper()
                tokens.append(letter)
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
    """目标冲突时自动加 _1/_2/_3，绝不覆盖。"""
    reserved = reserved or set()
    folder = os.path.dirname(path)
    name = os.path.basename(path)
    stem, ext = os.path.splitext(name)

    candidate = path
    idx = 1
    while os.path.exists(candidate) or candidate in reserved:
        candidate = os.path.join(folder, f"{stem}_{idx}{ext}")
        idx += 1
    return candidate


def make_preview_item(old_path: str, new_path: str, item_type: str) -> dict:
    """生成统一预览项。"""
    return {
        "old_path": old_path,
        "old_name": os.path.basename(old_path),
        "new_name": os.path.basename(new_path),
        "new_path": new_path,
        "type": item_type,
        "status": "待重命名",
    }


if __name__ == "__main__":
    root = tk.Tk()
    app = RenameApp(root)
    root.mainloop()
