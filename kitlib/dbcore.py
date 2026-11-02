"""SQLite 헬퍼 (stdlib). 스키마 적용, 테이블 일괄 교체(트랜잭션), 메타 KV, 계정(pbkdf2), 결과 저장.

    db = DB(path)                       # WAL, Row factory, 스레드 공유 OK (내부 RLock)
    db.apply_schema(sql)                # CREATE TABLE IF NOT EXISTS ... ; 여러 문장
    db.replace_tables({"t": (["c1","c2"], rows)})      # 전부 지우고 적재, 실패 시 롤백 → 기존 유지
    db.get_meta(k, default) / db.set_meta(k, v)
    db.seed_user(username, password, role) / db.check_password(username, password) → {"username","role"} | None
    db.save_result(kind, payload_dict, **cols) → id ; db.latest_result(kind) → dict(payload + id, created_at) ; db.results(kind, limit)
    db.counts(tables) → {t: n} ; db.q(sql, args) → list[dict] ; db.one(sql, args) → dict|None ; db.exec(sql, args)
    rows_to_tuples(rows, cols) → [tuple]  (dict 행 → 열 순서 튜플)
"""
import hashlib
import json
import os
import secrets
import sqlite3
import threading
from datetime import datetime

_BASE = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, role TEXT NOT NULL, pw_hash TEXT NOT NULL, salt TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS results (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, created_at TEXT, status TEXT, label TEXT, payload TEXT);
CREATE INDEX IF NOT EXISTS ix_results_kind ON results (kind, id);
"""


def _hash(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 100_000).hex()


def rows_to_tuples(rows, cols):
    return [tuple(r.get(c) for c in cols) for r in rows]


class DB:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        self.lock = threading.RLock()
        self.c = sqlite3.connect(path, check_same_thread=False, timeout=30)
        self.c.row_factory = sqlite3.Row
        self.c.execute("PRAGMA journal_mode=WAL")
        self.c.executescript(_BASE)
        self.c.commit()

    # --- basic
    def apply_schema(self, sql):
        with self.lock:
            self.c.executescript(sql)
            self.c.commit()

    def q(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.c.execute(sql, args)]

    def one(self, sql, args=()):
        with self.lock:
            r = self.c.execute(sql, args).fetchone()
            return dict(r) if r else None

    def exec(self, sql, args=()):
        with self.lock:
            cur = self.c.execute(sql, args)
            self.c.commit()
            return cur.lastrowid

    def counts(self, tables):
        return {t: self.one("SELECT COUNT(*) n FROM %s" % t)["n"] for t in tables}

    # --- bulk replace (transactional)
    def replace_tables(self, tables, meta=None):
        """tables: {name: (cols, rows_as_tuples_or_dicts)}. 전체가 하나의 트랜잭션."""
        with self.lock:
            try:
                self.c.execute("BEGIN")
                for name, (cols, rows) in tables.items():
                    self.c.execute("DELETE FROM %s" % name)
                    if rows and isinstance(rows[0], dict):
                        rows = rows_to_tuples(rows, cols)
                    self.c.executemany("INSERT INTO %s (%s) VALUES (%s)" % (name, ",".join(cols), ",".join("?" * len(cols))), rows)
                for k, v in (meta or {}).items():
                    self.c.execute("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, v))
                self.c.execute("COMMIT")
            except Exception:
                self.c.execute("ROLLBACK")
                raise

    # --- meta
    def get_meta(self, key, default=None):
        r = self.one("SELECT value FROM meta WHERE key=?", (key,))
        return r["value"] if r else default

    def set_meta(self, key, value):
        self.exec("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

    # --- users
    def seed_user(self, username, password, role, replace=False):
        if not password:
            return False
        if self.one("SELECT 1 FROM users WHERE username=?", (username,)) and not replace:
            return False
        salt = secrets.token_hex(8)
        self.exec("INSERT INTO users VALUES (?,?,?,?) ON CONFLICT(username) DO UPDATE SET role=excluded.role, pw_hash=excluded.pw_hash, salt=excluded.salt",
                  (username, role, _hash(password, salt), salt))
        return True

    def check_password(self, username, password):
        r = self.one("SELECT * FROM users WHERE username=?", (username,))
        if r and _hash(password or "", r["salt"]) == r["pw_hash"]:
            return {"username": username, "role": r["role"]}
        return None

    # --- results
    def save_result(self, kind, payload, status="current", label=None):
        with self.lock:
            try:
                self.c.execute("BEGIN")
                if status == "current":
                    self.c.execute("UPDATE results SET status='superseded' WHERE kind=? AND status='current'", (kind,))
                cur = self.c.execute("INSERT INTO results(kind, created_at, status, label, payload) VALUES (?,?,?,?,?)",
                                     (kind, datetime.now().isoformat(timespec="seconds"), status, label, json.dumps(payload, ensure_ascii=False)))
                self.c.execute("COMMIT")
                return cur.lastrowid
            except Exception:
                self.c.execute("ROLLBACK")
                raise

    def latest_result(self, kind):
        r = self.one("SELECT * FROM results WHERE kind=? AND status='current' ORDER BY id DESC LIMIT 1", (kind,))
        if not r:
            return None
        p = json.loads(r["payload"])
        p["_id"], p["_created_at"], p["_label"] = r["id"], r["created_at"], r["label"]
        return p

    def results(self, kind, limit=20):
        return self.q("SELECT id, created_at, status, label FROM results WHERE kind=? ORDER BY id DESC LIMIT ?", (kind, limit))
