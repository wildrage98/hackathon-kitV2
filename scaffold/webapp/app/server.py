"""기동: 스키마 → 계정 시드 → 빈 DB 면 data/provided 자동 적용 → 0.0.0.0:$PORT
실행: python3 -m app.server  (환경변수 .env.example)"""
import sys

from kitlib.webcore import serve

from . import api, config, datasets, specs, store
from .store import db


def bootstrap():
    store.seed_users()
    if not config.ADMIN_PASSWORD or not config.USER_PASSWORD:
        print("[server] 경고: ADMIN_PASSWORD / USER_PASSWORD 환경변수가 없어 로그인 계정이 생성되지 않습니다", file=sys.stderr)
    first = next(iter(specs.TABLES), None)
    if first and db.counts([first])[first] == 0:
        ok, res = datasets.apply("provided")
        print("[server] 빈 DB → data/provided 적용: %s" % (res["counts"] if ok else res["errors"][:3]), file=sys.stderr if not ok else sys.stdout)


def main():
    bootstrap()
    serve(api.app, config.HOST, config.PORT)


if __name__ == "__main__":
    main()
