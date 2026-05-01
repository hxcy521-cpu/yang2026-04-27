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
        self.root.title("批量转拼音重命名工具")
        self.root.geometry("1120x700")

        # 当前模式：folder 或 files
        self.mode = ""
        self.mode_text = tk.StringVar(value="当前模式：未选择")
        self.selected_path = tk.StringVar(value="")

        # 文件模式时保存用户选择的文件
        self.selected_files: list[str] = []

        # 预览项格式：dict(old_path, old_name, new_name, new_path, type, status)
        self.preview_items: list[dict] = []

        self._build_ui()

    def _build_ui(self) -> None:
        """构建图形界面。"""
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)

        ttk.Button(top_frame, text="选择文件夹", command=self.choose_folder).pack(side=tk.LEFT)
        ttk.Button(top_frame, text="选择文件", command=self.choose_files).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(top_frame, textvariable=self.mode_text).pack(side=tk.LEFT, padx=(18, 0))

        info_frame = ttk.Frame(self.root, padding=(10, 0, 10, 6))
        info_frame.pack(fill=tk.X)
        ttk.Label(info_frame, textvariable=self.selected_path, width=140).pack(side=tk.LEFT)

        action_frame = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        action_frame.pack(fill=tk.X)
        ttk.Button(action_frame, text="扫描预览", command=self.scan_preview).pack(side=tk.LEFT)
        ttk.Button(action_frame, text="开始重命名", command=self.rename_all).pack(side=tk.LEFT, padx=10)

        preview_frame = ttk.LabelFrame(self.root, text="预览列表", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("old_path", "old_name", "new_name", "status")
        self.tree = ttk.Treeview(preview_frame, columns=columns, show="headings", height=16)
        self.tree.heading("old_path", text="原路径")
        self.tree.heading("old_name", text="原名称")
        self.tree.heading("new_name", text="新名称")
        self.tree.heading("status", text="状态")

        self.tree.column("old_path", width=500)
        self.tree.column("old_name", width=180)
        self.tree.column("new_name", width=220)
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

    def log(self, message: str) -> None:
        """输出日志到界面。"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def choose_folder(self) -> None:
        """选择文件夹模式。"""
        path = filedialog.askdirectory(title="请选择要处理的文件夹")
        if path:
            self.mode = "folder"
            self.selected_files = []
            self.mode_text.set("当前模式：文件夹模式")
            self.selected_path.set(f"已选文件夹：{path}")
            self.log(f"已切换为文件夹模式：{path}")

    def choose_files(self) -> None:
        """选择文件模式，可多选文件。"""
        paths = filedialog.askopenfilenames(title="请选择要处理的文件（可多选）")
        if paths:
            self.mode = "files"
            self.selected_files = list(paths)
            self.mode_text.set("当前模式：文件模式")
            self.selected_path.set(f"已选文件数：{len(self.selected_files)}")
            self.log(f"已切换为文件模式，共选择 {len(self.selected_files)} 个文件")

    def convert_name(self, name: str, is_file: bool) -> str:
        """将名称转换为拼音，不改变文件扩展名。"""
        if is_file:
            stem, ext = split_filename(name)
            new_stem = normalize_to_pinyin(stem)
            return f"{new_stem or 'unnamed'}{ext}"
        return normalize_to_pinyin(name) or "unnamed_folder"

    def _clear_preview(self) -> None:
        self.preview_items.clear()
        for row in self.tree.get_children():
            self.tree.delete(row)

    def scan_preview(self) -> None:
        """扫描并生成预览，不会执行重命名。"""
        self._clear_preview()

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


def normalize_to_pinyin(text: str) -> str:
    """中文转拼音；英数保留；符号转下划线。"""
    chars = []
    for ch in text:
        if re.match(r"[\u4e00-\u9fff]", ch):
            chars.extend(lazy_pinyin(ch))
        elif re.match(r"[A-Za-z0-9]", ch):
            chars.append(ch)
        else:
            chars.append("_")
    result = "".join(chars)
    return re.sub(r"_+", "_", result).strip("_")


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
