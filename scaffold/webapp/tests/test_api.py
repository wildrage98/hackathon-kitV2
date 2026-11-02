"""API 기본: 헬스체크, 로그인·역할, 데이터셋 검증/적용, 생성·결과·내보내기. 임시 DB + 포트 0 (소켓 불가 환경이면 skip).
실행(프로젝트 폴더에서): python3 -m unittest discover -s tests -v"""
import json
import os
import shutil
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from http.cookiejar import CookieJar

TMP = tempfile.mkdtemp(prefix="webapp_test_")
os.environ["DB_PATH"] = os.path.join(TMP, "test.db")
os.environ["EXPORT_DIR"] = os.path.join(TMP, "exports")
os.environ["ADMIN_PASSWORD"] = "op-pass"
os.environ["USER_PASSWORD"] = "user-pass"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kitlib import webcore  # noqa: E402
from app import api, server  # noqa: E402


class Client:
    def __init__(self, base):
        self.base = base
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))

    def call(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(req, timeout=60) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode() or "{}")


class TestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not webcore.can_bind():
            raise unittest.SkipTest("socket bind not allowed")
        server.bootstrap()
        cls.srv = webcore.serve(api.app, "127.0.0.1", 0, block=False, quiet=True)
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        cls.op, cls.user, cls.anon = Client(cls.base), Client(cls.base), Client(cls.base)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        shutil.rmtree(TMP, ignore_errors=True)

    def test_01_health_auth_roles(self):
        st, h = self.anon.call("GET", "/health")
        self.assertEqual((st, h["status"]), (200, "ok"))
        self.assertEqual(self.anon.call("GET", "/api/datasets")[0], 401)
        self.assertEqual(self.op.call("POST", "/api/login", {"username": "admin", "password": "x"})[0], 401)
        st, d = self.op.call("POST", "/api/login", {"username": "admin", "password": "op-pass"})
        self.assertEqual((st, d["user"]["role"]), (200, "operator"))
        st, d = self.user.call("POST", "/api/login", {"username": "someone", "password": "user-pass"})
        self.assertIn(st, (200, 401))                       # USER_LOOKUP 설정 시 존재하는 아이디여야 200
        if st == 200:
            self.assertEqual(self.user.call("GET", "/api/datasets")[0], 403)

    def test_02_datasets(self):
        st, d = self.op.call("GET", "/api/datasets")
        self.assertEqual(st, 200)
        self.assertTrue(any(x["name"] == "provided" for x in d["datasets"]))
        st, v = self.op.call("POST", "/api/datasets/validate", {"name": "provided"})
        self.assertEqual(st, 200)
        self.assertIn("ok", v)
        self.assertEqual(self.op.call("POST", "/api/datasets/apply", {"name": "없는폴더"})[0], 400)

    def test_03_run_result_export(self):
        st, d = self.op.call("GET", "/api/run/defaults")
        self.assertEqual(st, 200)
        body = {f["name"]: f["value"] for f in d["fields"]}
        st, r = self.op.call("POST", "/api/run", body)
        self.assertEqual(st, 200, r)
        self.assertIn("verify", r)
        st, v = self.op.call("GET", "/api/result")
        self.assertEqual(st, 200)
        st, e = self.op.call("GET", "/api/result/export")
        self.assertEqual(st, 200)
        self.assertTrue(e["saved_to"].endswith(".json"))
        st, c = self.op.call("GET", "/api/result/verify")
        self.assertEqual(st, 200)
        self.assertIn("ok", c)


if __name__ == "__main__":
    unittest.main()
