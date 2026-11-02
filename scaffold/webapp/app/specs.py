"""데이터 정의 — 과제에 맞게 이 파일만 채우면 데이터셋 목록·검증·적용·조회가 동작한다.

SPECS      : CSV 파일별 열 규칙 (kitlib.csvschema.FileSpec / F). 참조(ref)는 파일 간 ID 무결성 검사.
CHECKS     : 파일 간 추가 검사 함수 [fn(data) -> [{file,row,column,code,message,(level:"warning")}]]
TABLES     : {테이블명: (열 목록, 원본 CSV 파일명)}  — 열 이름은 SPECS 의 열과 같아야 한다
SCHEMA_SQL : CREATE TABLE IF NOT EXISTS ... (TABLES 와 일치)
USER_LOOKUP: (테이블, 열) — 일반 사용자 로그인 아이디가 있어야 하는 곳. None 이면 아무 아이디나 허용.

아래는 예시 1개(items.csv). 과제 파일로 교체한다.
"""
from kitlib.csvschema import F, FileSpec

SPECS = [
    FileSpec("items.csv", {
        "item_id": F("str", unique=True),
        "name": F("str"),
        "qty": F("int", lo=0),
        "price": F("float", lo=0),
        "status": F("enum", enum=["ACTIVE", "INACTIVE"]),
    }),
]


def _check_example(data):
    """예시: 파일 간 검사. 문제 없으면 [] 반환."""
    return []


CHECKS = [_check_example]

TABLES = {
    "items": (["item_id", "name", "qty", "price", "status"], "items.csv"),
}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS items (item_id TEXT PRIMARY KEY, name TEXT, qty INTEGER, price REAL, status TEXT);
"""

USER_LOOKUP = None          # 예: ("employees", "emp_id")
