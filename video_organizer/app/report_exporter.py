import csv
from pathlib import Path
from openpyxl import Workbook

FIELDS = ["文件名", "原路径", "文件大小", "格式", "分辨率", "时长", "编码", "帧率", "修改时间", "建议分类", "是否重复"]


def rows_from_items(items: list[dict]) -> list[list]:
    rows = []
    for i in items:
        rows.append([
            i["name"], i["path"], i["size_text"], i["ext"], i["resolution"],
            i.get("duration", 0), i["codec"], i["fps"], i["modified"],
            i.get("suggested_category", ""), i.get("duplicate_type", i.get("duplicate", "")),
        ])
    return rows


def export_csv(items: list[dict], path: str):
    p = Path(path)
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(FIELDS)
        w.writerows(rows_from_items(items))


def export_excel(items: list[dict], path: str):
    wb = Workbook()
    ws = wb.active
    ws.title = "视频报表"
    ws.append(FIELDS)
    for row in rows_from_items(items):
        ws.append(row)
    wb.save(path)
