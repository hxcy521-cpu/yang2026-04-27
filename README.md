# D3_TOOL - 批量拼音重命名工具（Windows 10）

使用 **Python + tkinter** 开发的稳定版工具：批量把中文文件名/文件夹名改为拼音，且**不改变文件后缀**。

## 功能

- 两种处理模式：
  - **文件夹模式**：递归扫描所选文件夹下全部文件与子文件夹
  - **文件模式**：只处理用户手动选择的一个或多个文件
- 图形界面包含：
  - 拼音模式与分隔符规则设置
  - 选择文件夹
  - 选择文件
  - 当前模式显示
  - 扫描预览
  - 开始重命名
  - 导出预览CSV
  - 日志输出区
- 扫描后显示预览列表（原路径 / 原名称 / 新名称 / 状态）
- 必须先预览再执行重命名
- 执行前二次确认：
  - `请确认已备份重要文件，是否继续？`
- 重名冲突自动加 `_1`、`_2`、`_3`，绝不覆盖现有文件
- 生成 `rename_log.txt` 记录重命名结果
- 可勾选：
  - **仅重命名文件**
  - **仅重命名文件夹**
- 自动记住上次选择路径（`app_config.json`）
- 支持署名与 LOGO：
  - 界面署名：`By:印象视界_程阳`
  - 如果项目目录下存在 `logo.png`，将自动显示在界面右上角

## 命名规则

- 中文转拼音
- 英文和数字保留
- 空格和特殊符号转下划线 `_`
- 文件后缀保持不变

示例：

- `春节活动.mov` → `chunjiehuodong.mov`
- `舞台灯光图纸.pdf` → `wutaidengguangtuzhi.pdf`
- `测试.素材.v1.mov` → `ceshi_sucai_v1.mov`
- `LED素材文件夹` → `LEDsucaiwenjianjia`

## 安装依赖

```bash
python -m pip install -r requirements.txt
```

如果未安装 `pypinyin`，可直接执行：

```bash
python -m pip install pypinyin
```

## 运行

```bash
python main.py
```

## 打包为 EXE（PyInstaller）

```bash
python -m pip install pyinstaller
build_exe.bat
```

输出：`dist/PinyinRenamer.exe`

## 离线打包（内网/受限网络）

如果无法联网安装依赖，可使用离线方式：

1. 在可联网电脑执行：

```bash
python -m pip download -r requirements.txt
python -m pip download pyinstaller
```

2. 将下载得到的 `.whl/.tar.gz` 文件复制到本项目 `offline_pkgs` 目录。

3. 在 Windows 10 上双击运行：

```text
offline_build_exe.bat
```

脚本会自动执行离线安装并打包，最终 EXE 位置：

- `dist/中文转拼音重命名工具.exe`
