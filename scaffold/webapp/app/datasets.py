"""데이터셋(CSV 묶음) 목록·검증·적용. 업로드 없음: data/provided 와 data/datasets/<이름>/ 폴더에서 선택.
검증 통과 시에만 TABLES 전체를 한 트랜잭션으로 교체. 실패하면 기존 데이터·결과 유지."""
import datetime as dt
import os

from kitlib.csvschema import validate_folder

from . import config, specs
from .store import db

FILES = [sp.name for sp in specs.SPECS]


def dataset_dir(name):
    if name == "provided":
        return config.PROVIDED_DIR
    return os.path.join(config.DATASETS_DIR, os.path.basename(name))


def list_datasets():
    names = ["provided"]
    if os.path.isdir(config.DATASETS_DIR):
        names += sorted(d for d in os.listdir(config.DATASETS_DIR) if os.path.isdir(os.path.join(config.DATASETS_DIR, d)))
    active = db.get_meta("active_dataset")
    out = []
    for n in names:
        d = dataset_dir(n)
        present = [f for f in FILES if os.path.exists(os.path.join(d, f))]
        note = ""
        np_ = os.path.join(d, "NOTE.md")
        if os.path.exists(np_):
            with open(np_, encoding="utf-8") as f:
                lines = [x for x in f.read().splitlines() if x.strip()]
                note = lines[0] if lines else ""
        out.append({"name": n, "path": os.path.relpath(d, config.BASE_DIR), "files_present": len(present), "files_total": len(FILES),
                    "files_missing": [f for f in FILES if f not in present], "active": n == active, "note": note})
    return out


def validate(name):
    d = dataset_dir(name)
    if not os.path.isdir(d):
        return {"ok": False, "errors": [{"file": None, "row": None, "column": None, "code": "no_dataset", "message": "데이터셋 폴더 없음: %s" % name}],
                "warnings": [], "counts": {}, "data": {}}
    return validate_folder(d, specs.SPECS, specs.CHECKS)


def apply(name):
    res = validate(name)
    if not res["ok"]:
        return False, res
    tables = {}
    for table, (cols, fname) in specs.TABLES.items():
        rows = [r for r in res["data"].get(fname, []) if not r.get("_bad")]
        tables[table] = (cols, rows)
    now = dt.datetime.now().isoformat(timespec="seconds")
    db.replace_tables(tables, meta={"active_dataset": name, "active_dataset_applied_at": now})
    return True, res


def load_tables():
    return {t: db.q("SELECT * FROM %s" % t) for t in specs.TABLES}


def public(res):
    return {k: v for k, v in res.items() if k != "data"}


def state():
    """활성 데이터셋과 최신 결과의 정합성. stale = 결과 생성 이후 데이터셋이 바뀜."""
    active = db.get_meta("active_dataset")
    applied_at = db.get_meta("active_dataset_applied_at")
    res = db.latest_result("main")
    if not res:
        return {"active_dataset": active, "applied_at": applied_at, "result": None, "stale": False}
    stale = (res.get("dataset") != active) or (applied_at is not None and applied_at > res["_created_at"])
    return {"active_dataset": active, "applied_at": applied_at, "stale": stale,
            "result": {"id": res["_id"], "created_at": res["_created_at"], "dataset": res.get("dataset"), "params": res.get("params", {})}}
