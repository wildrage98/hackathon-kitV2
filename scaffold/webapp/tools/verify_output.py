"""내보낸 결과 JSON 을 현재 데이터로 다시 검증 (engine.verify). 실행: python3 tools/verify_output.py exports/result_*.json"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kitlib.verify import report_markdown  # noqa: E402
from app import datasets, engine  # noqa: E402


def main(path):
    result = json.load(open(path, encoding="utf-8"))
    out = engine.verify(result, datasets.load_tables())
    print(report_markdown(out))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
