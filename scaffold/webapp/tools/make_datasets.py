"""검증·시연용 데이터셋 생성 (재현 가능). data/provided 를 바탕으로 변경본(정상)·오류본을 data/datasets/<이름>/ 에 만든다.
각 폴더의 NOTE.md 첫 줄이 화면의 '메모'로 표시된다. 실행: python3 tools/make_datasets.py"""
import csv
import os
import shutil
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "data", "provided")
DST = os.path.join(BASE, "data", "datasets")
sys.path.insert(0, BASE)
from app import specs  # noqa: E402

FILES = [sp.name for sp in specs.SPECS]


def read(name):
    with open(os.path.join(SRC, name), encoding="utf-8-sig", newline="") as f:
        rd = csv.reader(f)
        return next(rd), list(rd)


def write(folder, name, header, rows):
    with open(os.path.join(folder, name), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def make(name, note, changes):
    """changes: {file: fn(header, rows) -> (header, rows) | (None, None)=파일 제외}. 나머지는 원본 복사."""
    folder = os.path.join(DST, name)
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)
    for fn in FILES:
        if fn in changes:
            h, r = changes[fn](*read(fn))
            if h is not None:
                write(folder, fn, h, r)
        elif os.path.exists(os.path.join(SRC, fn)):
            shutil.copy(os.path.join(SRC, fn), folder)
    with open(os.path.join(folder, "NOTE.md"), "w", encoding="utf-8") as f:
        f.write(note.strip() + "\n")
    print("made", name)


def drop_column(col):
    def fn(h, rows):
        i = h.index(col)
        return [c for j, c in enumerate(h) if j != i], [[c for j, c in enumerate(r) if j != i] for r in rows]
    return fn


def set_cell(row_idx, col, value):
    def fn(h, rows):
        rows[row_idx][h.index(col)] = value
        return h, rows
    return fn


def main():
    first = FILES[0]
    h, _ = read(first)
    # 과제에 맞게 아래를 바꾼다: 정상 변경본 1개 이상 + 오류본(필수 열 누락 / 참조 오류 / 형식 오류) 1개씩
    make("변경본_예시", "원본과 동일한 정상 변경본 예시 (내용을 과제에 맞게 바꾼다)", {})
    make("오류본_필수열누락", "%s 에서 %s 열 제거 → missing_column" % (first, h[-1]), {first: drop_column(h[-1])})
    make("오류본_형식오류", "%s 1행 %s 에 잘못된 값 → bad_value" % (first, h[-1]), {first: set_cell(0, h[-1], "???")})


if __name__ == "__main__":
    main()
