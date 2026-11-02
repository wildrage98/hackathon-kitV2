"""DB 핸들 1개 (kitlib.dbcore.DB). 스키마는 specs.SCHEMA_SQL."""
from kitlib.dbcore import DB

from . import config, specs

db = DB(config.DB_PATH)
db.apply_schema(specs.SCHEMA_SQL)


def seed_users():
    db.seed_user(config.ADMIN_USER, config.ADMIN_PASSWORD, "operator")
    db.seed_user("__user__", config.USER_PASSWORD, "user")


def login(username, password):
    """운영자: users 테이블. 일반 사용자: 아이디(USER_LOOKUP 로 존재 확인) + 공통 비밀번호."""
    u = db.check_password(username, password)
    if u and u["role"] == "operator":
        return {"username": username, "role": "operator"}
    common = db.check_password("__user__", password)
    if not common:
        return None
    if specs.USER_LOOKUP:
        table, col = specs.USER_LOOKUP
        row = db.one("SELECT * FROM %s WHERE %s=?" % (table, col), (username,))
        if not row:
            return None
        return {"username": username, "role": "user", "profile": row}
    return {"username": username, "role": "user", "profile": {}}
