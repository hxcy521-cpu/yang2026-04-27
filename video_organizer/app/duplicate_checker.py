import hashlib
from collections import defaultdict
from pathlib import Path


def mark_suspected_duplicates(items: list[dict]) -> None:
    by_name = defaultdict(list)
    by_size = defaultdict(list)
    for i, item in enumerate(items):
        by_name[item["name"]].append(i)
        by_size[item["size_bytes"]].append(i)

    dup_idx = set()
    for group in list(by_name.values()) + list(by_size.values()):
        if len(group) > 1:
            dup_idx.update(group)

    for i, item in enumerate(items):
        if i in dup_idx:
            item["duplicate"] = "是"
            item["duplicate_type"] = "疑似重复"
        else:
            item["duplicate"] = "否"
            item["duplicate_type"] = ""


def file_hash(path: Path, algo="md5", chunk_size=4 * 1024 * 1024) -> str:
    h = hashlib.new(algo)
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def mark_exact_duplicates(items: list[dict], algo="md5"):
    hash_map = defaultdict(list)
    for idx, item in enumerate(items):
        try:
            digest = file_hash(Path(item["path"]), algo=algo)
            hash_map[digest].append(idx)
        except Exception:
            continue
    for idxs in hash_map.values():
        if len(idxs) > 1:
            for i in idxs:
                items[i]["duplicate"] = "是"
                items[i]["duplicate_type"] = "完全重复"
