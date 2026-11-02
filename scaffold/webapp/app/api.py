"""HTTP API (역할: operator / user). 도메인 로직은 engine.py, 데이터 정의는 specs.py 에만 둔다."""
import datetime as dt
import json
import os

from kitlib.verify import report_markdown
from kitlib.webcore import App, HttpError, Response

from . import config, datasets, engine, store
from .store import db

app = App(static_dir=config.WEB_DIR, session_secret=config.SECRET_KEY, session_ttl_min=config.SESSION_TTL_MIN)


def require(req, role=None):
    if not req.user:
        raise HttpError(401, "로그인 필요")
    if role and req.user["role"] != role:
        raise HttpError(403, "%s 권한 필요" % ("운영자" if role == "operator" else "사용자"))
    return req.user


def _current(require_fresh=False):
    st = datasets.state()
    res = db.latest_result("main")
    if not res:
        raise HttpError(404, "아직 생성된 결과가 없습니다")
    if require_fresh and st["stale"]:
        raise HttpError(409, "데이터가 변경되어 결과를 다시 생성해야 합니다 (재생성 전까지 이전 결과는 표시하지 않습니다)")
    return res, st


# ----------------------------------------------------------------------------- health / auth
@app.route("GET", "/health")
def health(req):
    try:
        counts = db.counts(list(datasets.specs.TABLES))
    except Exception as e:  # noqa: BLE001
        return 503, {"status": "error", "error": str(e)}
    st = datasets.state()
    return {"status": "ok", "app": config.APP_NAME, "db": os.path.basename(config.DB_PATH), "active_dataset": st["active_dataset"], "tables": counts,
            "result": st["result"]["id"] if st["result"] else None, "stale": st["stale"], "time": dt.datetime.now().isoformat(timespec="seconds")}


@app.route("POST", "/api/login")
def login(req):
    body = req.json()
    u = store.login((body.get("username") or "").strip(), body.get("password") or "")
    if not u:
        raise HttpError(401, "아이디 또는 비밀번호가 맞지 않습니다")
    req.set_cookie(app.cookie_name, app.sessions.create(u), max_age=config.SESSION_TTL_MIN * 60)
    return {"user": {k: v for k, v in u.items() if k != "profile"}}


@app.route("POST", "/api/logout")
def logout(req):
    app.sessions.drop(req.cookies.get(app.cookie_name))
    req.set_cookie(app.cookie_name, "", max_age=0)
    return {"ok": True}


@app.route("GET", "/api/me")
def me(req):
    u = {k: v for k, v in req.user.items() if k != "profile"} if req.user else None
    return {"user": u, "state": datasets.state()}


# ----------------------------------------------------------------------------- datasets (operator)
@app.route("GET", "/api/datasets")
def list_ds(req):
    require(req, "operator")
    st = datasets.state()
    return {"datasets": datasets.list_datasets(), "active": st["active_dataset"], "applied_at": st["applied_at"]}


@app.route("POST", "/api/datasets/validate")
def validate_ds(req):
    require(req, "operator")
    name = (req.json().get("name") or "").strip()
    return {"name": name, **datasets.public(datasets.validate(name))}


@app.route("POST", "/api/datasets/apply")
def apply_ds(req):
    require(req, "operator")
    name = (req.json().get("name") or "").strip()
    ok, res = datasets.apply(name)
    if not ok:
        return 400, {"applied": False, "ok": False, "name": name, "message": "검증 실패 — 기존 데이터와 결과를 유지합니다", **datasets.public(res)}
    return {"applied": True, "ok": True, "name": name, "counts": res["counts"], "errors": [], "warnings": res["warnings"], "state": datasets.state(),
            "message": "적용 완료 — 이전 결과는 재생성 전까지 '이전 데이터 기준'으로 표시됩니다"}


# ----------------------------------------------------------------------------- run / result (operator)
@app.route("GET", "/api/run/defaults")
def run_defaults(req):
    require(req, "operator")
    last = db.latest_result("main")
    cur = dict(last.get("params", {})) if last else {}
    fields = []
    for p in engine.PARAMS:
        f = dict(p)
        f["value"] = cur.get(p["name"], p.get("default"))
        fields.append(f)
    return {"fields": fields, "filters": engine.FILTERS}


@app.route("POST", "/api/run")
def run(req):
    require(req, "operator")
    body = req.json()
    params = {}
    for p in engine.PARAMS:
        v = body.get(p["name"], p.get("default"))
        if p.get("type") == "number":
            try:
                v = float(v)
                v = int(v) if v == int(v) else v
            except (TypeError, ValueError):
                raise HttpError(400, "%s: 숫자여야 합니다" % p["label"])
            if p.get("min") is not None and v < p["min"]:
                raise HttpError(400, "%s: 최소 %s" % (p["label"], p["min"]))
        params[p["name"]] = v
    tables = datasets.load_tables()
    dataset = db.get_meta("active_dataset") or "provided"
    try:
        result = engine.run(tables, params, dataset)
    except ValueError as e:
        raise HttpError(422, "생성 불가: %s" % e)
    chk = engine.verify(result, tables)
    result["verify"] = {"ok": chk["ok"], "counts": chk["counts"]}
    rid = db.save_result("main", result, label=dataset)
    return {"result_id": rid, "verify": result["verify"], "state": datasets.state(), "view": engine.view(result, {})}


@app.route("GET", "/api/result")
def result(req):
    require(req, "operator")
    res, st = _current()
    v = engine.view(res, req.query)
    v["stale"] = st["stale"]
    v["result"] = st["result"]
    return v


@app.route("GET", "/api/result/verify")
def result_verify(req):
    require(req, "operator")
    res, st = _current()
    chk = engine.verify(res, datasets.load_tables())
    return {"stale": st["stale"], **chk, "markdown": report_markdown(chk)}


@app.route("GET", "/api/result/export")
def export(req):
    require(req, "operator")
    res, st = _current()
    payload = {k: v for k, v in res.items() if not k.startswith("_")}
    os.makedirs(config.EXPORT_DIR, exist_ok=True)
    fn = "result_%s_%s.json" % (res.get("dataset", "data"), res["_created_at"].replace(":", "").replace("-", "")[:15])
    path = os.path.join(config.EXPORT_DIR, fn)
    body = json.dumps(payload, ensure_ascii=False, indent=1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    if req.query.get("raw"):
        return Response(body, 200, "application/json; charset=utf-8")
    return {"stale": st["stale"], "saved_to": os.path.relpath(path, config.BASE_DIR), "bytes": len(body.encode()), "json": body}


# ----------------------------------------------------------------------------- user
@app.route("GET", "/api/me/result")
def my_result(req):
    u = require(req, "user")
    res, st = _current(require_fresh=True)
    return engine.user_view(res, u, req.query)
