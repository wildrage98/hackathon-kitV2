"""미니 웹 프레임워크 (stdlib). 라우팅·JSON·정적 파일·SPA 폴백·서명 세션 쿠키·0.0.0.0.

    app = App(static_dir="web", session_secret=SECRET)
    @app.route("GET", "/api/x/<id>")  →  def h(req, id): return {"id": id}
    req: method path query headers cookies json() body() user set_cookie()
    반환: dict/list → JSON 200 | (status, dict) | Response(body, status, content_type) | str → html
    HttpError(status, msg, **extra) → {"error": msg, ...}
    app.sessions.create(user)/get(tok)/drop(tok)   can_bind(host, port)   serve(app, host, port, block=True, quiet=False)
"""
import hashlib
import hmac
import json
import mimetypes
import os
import re
import secrets
import socket
import sys
import threading
import time
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


class HttpError(Exception):
    def __init__(self, status, message, **extra):
        super().__init__(message)
        self.status, self.message, self.extra = status, message, extra


class Response:
    def __init__(self, body=b"", status=200, content_type="application/json; charset=utf-8", headers=None):
        self.body = body if isinstance(body, (bytes, bytearray)) else str(body).encode("utf-8")
        self.status, self.content_type, self.headers = status, content_type, headers or []


class Request:
    def __init__(self, handler):
        self.h = handler
        self.method = handler.command
        u = urlsplit(handler.path)
        self.path = u.path
        self.query = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(u.query, keep_blank_values=True).items()}
        self.headers = handler.headers
        self.cookies = {}
        for part in (handler.headers.get("Cookie") or "").split(";"):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                self.cookies[k] = v
        self._body = None
        self.user = None
        self.set_cookies = []

    def body(self):
        if self._body is None:
            n = int(self.headers.get("Content-Length") or 0)
            self._body = self.h.rfile.read(n) if n else b""
        return self._body

    def json(self):
        raw = self.body()
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except ValueError:
            raise HttpError(400, "JSON 본문이 아님")

    def set_cookie(self, name, value, max_age=None, http_only=True, path="/"):
        c = "%s=%s; Path=%s; SameSite=Lax" % (name, value, path)
        if max_age is not None:
            c += "; Max-Age=%d" % max_age
        if http_only:
            c += "; HttpOnly"
        self.set_cookies.append(c)


class Sessions:
    """서명된 토큰 + 서버 메모리 저장. 재시작 시 세션만 사라진다(데이터는 DB)."""

    def __init__(self, secret, ttl_min=480):
        self.secret, self.ttl = secret.encode(), ttl_min * 60
        self.store, self.lock = {}, threading.Lock()

    def _sign(self, raw):
        return hmac.new(self.secret, raw.encode(), hashlib.sha256).hexdigest()[:24]

    def create(self, user):
        raw = secrets.token_urlsafe(18)
        tok = raw + "." + self._sign(raw)
        with self.lock:
            self.store[tok] = (user, time.time() + self.ttl)
        return tok

    def get(self, tok):
        if not tok or "." not in tok:
            return None
        raw, sig = tok.rsplit(".", 1)
        if not hmac.compare_digest(sig, self._sign(raw)):
            return None
        with self.lock:
            v = self.store.get(tok)
            if not v:
                return None
            if v[1] < time.time():
                self.store.pop(tok, None)
                return None
            return v[0]

    def drop(self, tok):
        with self.lock:
            self.store.pop(tok, None)


class App:
    def __init__(self, static_dir=None, index="index.html", session_secret="dev", session_ttl_min=480, cookie_name="sid"):
        self.routes = []
        self.static_dir, self.index = static_dir, index
        self.sessions = Sessions(session_secret, session_ttl_min)
        self.cookie_name = cookie_name
        self.before = []

    def route(self, method, pattern):
        rx = re.compile("^" + re.sub(r"<(\w+)>", r"(?P<\1>[^/]+)", pattern) + "$")

        def deco(fn):
            self.routes.append((method.upper(), rx, fn))
            return fn
        return deco

    def dispatch(self, req):
        req.user = self.sessions.get(req.cookies.get(self.cookie_name))
        for fn in self.before:
            fn(req)
        for method, rx, fn in self.routes:
            m = rx.match(req.path)
            if m and method == req.method:
                return fn(req, **m.groupdict())
        if req.method in ("GET", "HEAD") and self.static_dir:
            return self._static(req.path)
        raise HttpError(404, "경로 없음: %s %s" % (req.method, req.path))

    def _static(self, path):
        rel = path.lstrip("/") or self.index
        full = os.path.normpath(os.path.join(self.static_dir, rel))
        if not full.startswith(os.path.normpath(self.static_dir)):
            raise HttpError(403, "금지")
        if os.path.isdir(full):
            full = os.path.join(full, self.index)
        if not os.path.isfile(full):
            if "." not in os.path.basename(rel):       # SPA 폴백
                full = os.path.join(self.static_dir, self.index)
            if not os.path.isfile(full):
                raise HttpError(404, "파일 없음")
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        with open(full, "rb") as f:
            return Response(f.read(), 200, ctype, [("Cache-Control", "no-cache")])


def _to_response(ret):
    if isinstance(ret, Response):
        return ret
    status = 200
    if isinstance(ret, tuple) and len(ret) == 2 and isinstance(ret[0], int):
        status, ret = ret
    if isinstance(ret, (dict, list)):
        return Response(json.dumps(ret, ensure_ascii=False), status)
    if ret is None:
        return Response(b"", 204)
    return Response(str(ret), status, "text/html; charset=utf-8")


def make_handler(app, quiet=False):
    class H(BaseHTTPRequestHandler):
        server_version = "kit/1.0"
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            if not quiet:
                sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

        def _handle(self):
            req = Request(self)
            try:
                resp = _to_response(app.dispatch(req))
            except HttpError as e:
                resp = Response(json.dumps({"error": e.message, **e.extra}, ensure_ascii=False), e.status)
            except Exception:  # noqa: BLE001
                traceback.print_exc()
                resp = Response(json.dumps({"error": "서버 내부 오류"}), 500)
            try:
                req.body()   # 본문을 다 읽어야 keep-alive 가 깨지지 않는다
            except Exception:  # noqa: BLE001
                pass
            self.send_response(resp.status)
            self.send_header("Content-Type", resp.content_type)
            self.send_header("Content-Length", str(len(resp.body)))
            for k, v in resp.headers:
                self.send_header(k, v)
            for c in req.set_cookies:
                self.send_header("Set-Cookie", c)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(resp.body)

        do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = do_PATCH = _handle
    return H


def can_bind(host="0.0.0.0", port=0):
    try:
        s = socket.socket()
        s.bind((host, port))
        s.close()
        return True
    except OSError:
        return False


def serve(app, host="0.0.0.0", port=8000, block=True, quiet=False):
    srv = ThreadingHTTPServer((host, port), make_handler(app, quiet))
    srv.daemon_threads = True
    print("[server] listening on http://%s:%d" % (host, srv.server_address[1]), flush=True)
    if block:
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            srv.server_close()
    else:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
