"""도메인 로직 — 과제의 '생성/계산' 부분. 이 파일의 네 함수만 채우면 화면·API·내보내기가 붙는다.

PARAMS  : 실행 폼 필드 [{name, label, type: number|text|date|select, default, min?, step?, options?}]
run(tables, params)        → result dict (JSON 직렬화 가능, 내보내기 본문). 반드시 "dataset" 과 "params" 를 포함할 것(아래 _base 사용).
view(result, query)        → 운영자 화면 뷰 스펙. query 는 화면 필터값 dict.
user_view(result, user, query) → 일반 사용자 화면 뷰 스펙 (user["username"], user["profile"]).
verify(result, tables)     → {"ok", "violations", "counts", "checked"}  (kitlib.verify.Violations) — 규칙을 생성 코드와 별도로 다시 센다.

뷰 스펙 (web/app.js 가 그대로 그린다):
  {"title": str, "notice": str, "filters": [{"name","label","options":[..],"value"}],
   "metrics": [{"k": 라벨, "v": 값, "sub": 보조}], "tables": [{"title","columns":[..],"rows":[[..]],"key"?: 열인덱스}],
   "graph": {"nodes":[{"id","name","kind":"site|stop","x","y"}], "edges":[{"id","path":[ids],"color":int,"label"}], "marks":[{"x","y","label"}]},
   "timeline": [{"time","label","note","me":bool,"kind"}], "text": 마크다운 비슷한 평문}
아래는 테이블 행 수를 세는 예시 구현이다. 과제 로직으로 교체한다.
"""
import datetime as dt

from kitlib.verify import Violations

PARAMS = [
    {"name": "limit", "label": "미리보기 행 수", "type": "number", "default": 10, "min": 1},
    {"name": "note", "label": "메모", "type": "text", "default": ""},
]

FILTERS = []        # 운영자 결과 화면 필터 예: [{"name": "date", "label": "날짜"}]


def _base(tables, params, dataset):
    return {"schema_version": "1.0", "generated_at": dt.datetime.now().isoformat(timespec="seconds"), "dataset": dataset, "params": params}


def run(tables, params, dataset):
    limit = int(params.get("limit", 10))
    out = _base(tables, params, dataset)
    out["counts"] = {t: len(rows) for t, rows in tables.items()}
    out["preview"] = {t: rows[:limit] for t, rows in tables.items()}
    return out


def view(result, query):
    tables = []
    for t, rows in result.get("preview", {}).items():
        cols = list(rows[0].keys()) if rows else []
        tables.append({"title": "%s (처음 %d행)" % (t, len(rows)), "columns": cols, "rows": [[r.get(c) for c in cols] for r in rows]})
    return {"title": "결과 (예시: 행 수 집계)", "metrics": [{"k": t, "v": n, "sub": "행"} for t, n in result.get("counts", {}).items()],
            "tables": tables, "text": "engine.py 의 run/view/user_view/verify 를 과제 로직으로 교체한다."}


def user_view(result, user, query):
    return {"title": "내 정보", "metrics": [{"k": "아이디", "v": user["username"]}], "text": "일반 사용자 화면 — engine.user_view 에서 구성"}


def verify(result, tables):
    v = Violations()
    for t, n in result.get("counts", {}).items():
        if n != len(tables.get(t, [])):
            v.add("count_mismatch", "%s: 결과 %d ≠ 현재 데이터 %d" % (t, n, len(tables.get(t, []))), table=t)
    return v.result(checked={"tables": len(result.get("counts", {}))})
