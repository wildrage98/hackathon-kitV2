"""선언형 CSV 묶음 검증 (stdlib).

    F(type="str|int|float|bool|date|time|enum", required=True, unique=False, enum=None, ref=("file.csv","col") | [(..),(..)],
      lo=None, hi=None, pattern=None, allow_blank=False)
    FileSpec(name, {col: F(...)}, pk=["a","b"], required=True)
    validate_folder(folder, specs, checks=[fn(data)->[{file,row,column,code,message,level?}]])
      → {"ok", "errors":[{file,row,column,code,message}], "warnings", "counts":{file: 정상행수}, "data":{file:[row dict + _row,_bad]}}
    순서: 파일 → 필수 열 → 셀(type/enum/범위/pattern) → unique/pk 중복 → ref 참조 → checks.  셀 오류 행도 data 에 남긴다(_bad=True, 참조 연쇄 방지).
    errors_markdown(result, limit=50)
    코드: missing_file unreadable empty missing_column short_row bad_value duplicate duplicate_key bad_ref check_failed truncated
"""
import csv
import os
import re
from datetime import datetime

MAX_ERRORS_PER_FILE = 100


class F:
    """열 규칙. type: str|int|float|bool|date|time|enum. ref=("file.csv","column") 참조 무결성."""

    def __init__(self, type="str", required=True, unique=False, enum=None, ref=None, lo=None, hi=None, pattern=None, allow_blank=False):
        self.type, self.required, self.unique, self.enum, self.ref = type, required, unique, enum, ref
        self.lo, self.hi, self.pattern, self.allow_blank = lo, hi, re.compile(pattern) if pattern else None, allow_blank


class FileSpec:
    def __init__(self, name, fields, pk=None, required=True):
        self.name, self.fields, self.pk, self.required = name, fields, pk or [], required


def _read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rd = csv.reader(f)
        header = next(rd, None)
        rows = [r for r in rd]
    return header, rows


def _conv(f, raw):
    """(ok, value, msg)"""
    s = (raw or "").strip()
    if s == "" or s.lower() in ("na", "n/a", "null", "none"):
        if f.required and not f.allow_blank:
            return False, None, "값 없음"
        return True, None, None
    t = f.type
    try:
        if t == "int":
            v = int(float(s)) if re.fullmatch(r"-?\d+(\.0+)?", s) else int(s)
        elif t == "float":
            v = float(s)
        elif t == "bool":
            if s.lower() in ("true", "1", "y", "yes"):
                v = True
            elif s.lower() in ("false", "0", "n", "no"):
                v = False
            else:
                return False, None, "true/false 아님: %r" % s
        elif t == "date":
            v = datetime.strptime(s, "%Y-%m-%d").date().isoformat()
        elif t == "time":
            if not re.fullmatch(r"\d{1,2}:\d{2}", s):
                return False, None, "HH:MM 아님: %r" % s
            h, m = map(int, s.split(":"))
            if not (0 <= h <= 24 and 0 <= m < 60):
                return False, None, "시각 범위 밖: %r" % s
            v = "%02d:%02d" % (h, m)
        elif t == "enum":
            v = s
            if f.enum is not None and s not in f.enum:
                return False, None, "허용값 아님: %r (허용: %s)" % (s, ",".join(map(str, f.enum)))
        else:
            v = s
    except ValueError:
        return False, None, "%s 형식 아님: %r" % (t, s)
    if f.enum is not None and t != "enum" and v not in f.enum:
        return False, None, "허용값 아님: %r" % s
    if f.lo is not None and v is not None and isinstance(v, (int, float)) and v < f.lo:
        return False, None, "하한 %s 미만: %s" % (f.lo, v)
    if f.hi is not None and v is not None and isinstance(v, (int, float)) and v > f.hi:
        return False, None, "상한 %s 초과: %s" % (f.hi, v)
    if f.pattern and isinstance(v, str) and not f.pattern.fullmatch(v):
        return False, None, "형식 불일치: %r" % s
    return True, v, None


def validate_folder(folder, specs, checks=None):
    errors, warnings, counts, data = [], [], {}, {}
    overflow = {}

    def err(file, row, col, code, msg):
        if sum(1 for e in errors if e["file"] == file) >= MAX_ERRORS_PER_FILE:
            overflow[file] = overflow.get(file, 0) + 1
            return
        errors.append({"file": file, "row": row, "column": col, "code": code, "message": msg})

    # 1) 파일·열·셀
    for sp in specs:
        path = os.path.join(folder, sp.name)
        if not os.path.exists(path):
            if sp.required:
                err(sp.name, None, None, "missing_file", "파일 없음")
            continue
        try:
            header, rows = _read(path)
        except Exception as e:  # noqa: BLE001
            err(sp.name, None, None, "unreadable", "읽기 실패: %s" % e)
            continue
        if header is None:
            err(sp.name, None, None, "empty", "빈 파일")
            continue
        header = [h.strip() for h in header]
        missing = [c for c, f in sp.fields.items() if f.required and c not in header]
        for c in missing:
            err(sp.name, 1, c, "missing_column", "필수 열 누락")
        if missing:
            continue
        idx = {c: header.index(c) for c in sp.fields if c in header}
        out = []
        seen = {c: {} for c, f in sp.fields.items() if f.unique}
        pk_seen = {}
        for i, r in enumerate(rows, start=2):
            if not any(x.strip() for x in r):
                continue
            if len(r) < len(header):
                err(sp.name, i, None, "short_row", "열 개수 부족 (%d/%d)" % (len(r), len(header)))
                continue
            rec, bad = {}, False
            for c, f in sp.fields.items():
                if c not in idx:
                    rec[c] = None
                    continue
                ok, v, msg = _conv(f, r[idx[c]])
                if not ok:
                    err(sp.name, i, c, "bad_value", msg)
                    bad = True
                rec[c] = v
            for c in seen:
                v = rec.get(c)
                if v is None:
                    continue
                if v in seen[c]:
                    err(sp.name, i, c, "duplicate", "중복 (처음: %d행)" % seen[c][v])
                else:
                    seen[c][v] = i
            if sp.pk and all(rec.get(c) is not None for c in sp.pk):
                k = tuple(rec[c] for c in sp.pk)
                if k in pk_seen:
                    err(sp.name, i, "+".join(sp.pk), "duplicate_key", "키 중복 %s (처음: %d행)" % (k, pk_seen[k]))
                else:
                    pk_seen[k] = i
            rec["_row"] = i
            rec["_bad"] = bad          # 셀 오류가 있어도 행은 남긴다 (키가 살아 있으면 참조 오류가 연쇄되지 않게)
            out.append(rec)
        data[sp.name] = out
        counts[sp.name] = sum(1 for r in out if not r["_bad"])

    # 2) 참조 무결성
    keysets = {}

    def keyset(file, col):
        kk = (file, col)
        if kk not in keysets:
            keysets[kk] = {r[col] for r in data.get(file, []) if r.get(col) is not None}
        return keysets[kk]

    for sp in specs:
        for c, f in sp.fields.items():
            if not f.ref or sp.name not in data:
                continue
            refs = f.ref if isinstance(f.ref, list) else [f.ref]
            allowed = set()
            for rf, rc in refs:
                allowed |= keyset(rf, rc)
            if not allowed and any(rf not in data for rf, _ in refs):
                continue  # 참조 대상 파일 자체가 실패 → 이미 보고됨
            for r in data[sp.name]:
                v = r.get(c)
                if v is not None and v not in allowed:
                    err(sp.name, r["_row"], c, "bad_ref", "존재하지 않는 ID: %r (참조: %s)" % (v, ", ".join("%s.%s" % x for x in refs)))

    # 3) 파일 간 검사
    for fn in checks or []:
        try:
            for e in fn(data) or []:
                if e.get("level") == "warning":
                    warnings.append(e)
                else:
                    err(e.get("file"), e.get("row"), e.get("column"), e.get("code", "check"), e.get("message"))
        except Exception as ex:  # noqa: BLE001
            err(None, None, None, "check_failed", "검사 실행 실패: %s" % ex)

    for f, n in overflow.items():
        warnings.append({"file": f, "row": None, "column": None, "code": "truncated", "message": "오류 %d건 더 있음 (표시 생략)" % n})
    return {"ok": not errors, "errors": errors, "warnings": warnings, "counts": counts, "data": data}


def errors_markdown(result, limit=50):
    if result["ok"]:
        return "검증 통과: " + ", ".join("%s %d행" % kv for kv in result["counts"].items())
    lines = ["| 파일 | 행 | 열 | 코드 | 내용 |", "|---|---|---|---|---|"]
    for e in result["errors"][:limit]:
        lines.append("| %s | %s | %s | %s | %s |" % (e["file"], e["row"] or "", e["column"] or "", e["code"], e["message"]))
    if len(result["errors"]) > limit:
        lines.append("… 외 %d건" % (len(result["errors"]) - limit))
    return "\n".join(lines)
