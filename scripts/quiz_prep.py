#!/usr/bin/env python3
"""quiz_prep.py — 제출 후 "이해도 확인"(6문항 × 5분, 복사 불가) 대비: 문서 훅 점검 + 암기 재료 수집 (stdlib only, Python 3.8+).

  python3 tools/quiz_prep.py --project <폴더>      # → docs/QUIZ_CARD.md, 훅 상태·남은 (채움 출력
  python3 tools/quiz_prep.py --project <폴더> -q   # 상태만

질문은 제출물(HOW_TO_RUN · AI_COLLABORATION · 코드)에서 생성되므로, 질문의 출처가 될 굵은 소제목 6개(훅)가
채워져 있는지와 답에 쓸 식별자(파일·테스트·API·환경변수·명령·숫자·로그)를 한 파일로 모은다.
그 다음 에이전트가 hackathon-kit/prompts/09-quiz.md 로 docs/QUIZ.md(답 초안)를 쓴다.

종료 코드: 0 = 훅 6개 채움 + (채움 없음 / 1 = 남은 것 있음 / 2 = HOW_TO_RUN 을 못 찾음
"""
from __future__ import annotations

import glob
import os
import re
import sys

HOOKS = [
    ("구조 선택", r"\*\*구조 선택"),
    ("모듈과 상태", r"\*\*모듈과 상태"),
    ("잘못된 입력·어긋난 순서", r"\*\*잘못된 입력"),
    ("설계 기준과 최적화 방식", r"\*\*설계 기준"),
    ("조건을 바꾸면", r"\*\*조건을 바꾸면"),
    ("검증함 / 가정함 / 미구현", r"\*\*검증함"),
]
PLACEHOLDER = "(채움"
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "hackathon-kit", "hackathon-kitV2"}


# ----------------------------------------------------------------------------- 문서 점검
def hook_status(text):
    """[(이름, '채움'|'빈칸'|'없음', 본문 글자 수)] — 라벨부터 다음 굵은 라벨/## 제목 전까지를 블록으로 본다."""
    out = []
    for name, pat in HOOKS:
        m = re.search(pat, text)
        if not m:
            out.append((name, "없음", 0))
            continue
        rest = text[m.end():]
        nxt = re.search(r"\n(?:\*\*[^\n]{2,40}\*\*|## )", rest)
        block = rest[: nxt.start()] if nxt else rest
        body = re.sub(r"^[^\n]*\n", "", block, count=1)              # 라벨 줄 제거
        body_text = re.sub(r"\s+", "", body)
        if PLACEHOLDER in block or len(body_text) < 30:
            out.append((name, "빈칸", len(body_text)))
        else:
            out.append((name, "채움", len(body_text)))
    return out


def placeholder_count(text):
    return text.count(PLACEHOLDER)


def quiz_status(path):
    """docs/QUIZ.md: (존재, 답 섹션 수, 남은 (채움 수)"""
    if not os.path.exists(path):
        return (False, 0, 0)
    t = open(path, encoding="utf-8", errors="ignore").read()
    return (True, len(re.findall(r"^## Q\d", t, re.M)), placeholder_count(t))


# ----------------------------------------------------------------------------- 재료 수집
def _read(p):
    try:
        return open(p, encoding="utf-8", errors="ignore").read()
    except OSError:
        return ""


def first_docstring(path):
    head = _read(path)[:1500]
    m = re.search(r"(?:\"\"\"|''')\s*([^\n]{3,160})", head)
    return m.group(1).replace('\"\"\"', "").replace("'''", "").strip() if m else ""


def collect_tests(project):
    items = []
    for p in sorted(glob.glob(os.path.join(project, "tests", "test_*.py"))):
        src = _read(p)
        for m in re.finditer(r"def (test_\w+)\([^)]*\):\s*\n\s*(?:(?:\"\"\"|''')([^\n]*))?", src):
            doc = (m.group(2) or "").replace('\"\"\"', "").replace("'''", "").strip()
            items.append((os.path.relpath(p, project), m.group(1), doc))
    return items


def collect_routes(project):
    out = []
    for p in sorted(glob.glob(os.path.join(project, "app", "*.py"))):
        for m in re.finditer(r"@app\.route\(\s*\"(\w+)\"\s*,\s*\"([^\"]+)\"", _read(p)):
            out.append("%s %s" % (m.group(1), m.group(2)))
    return out


def collect_env(project):
    out = []
    for cand in (os.path.join(project, ".env.example"), ".env.example"):
        if os.path.exists(cand):
            out = re.findall(r"^([A-Z][A-Z0-9_]+)=", _read(cand), re.M)
            break
    return out


def collect_commands(text):
    cmds = []
    for block in re.findall(r"```[a-z]*\n(.*?)```", text, re.S):
        for line in block.splitlines():
            s = line.strip()
            if re.match(r"(python3?|bash|docker|cp|curl|sh)\s", s) and s not in cmds:
                cmds.append(s)
    return cmds[:12]


def collect_numbers(text):
    out, seen = [], set()
    for line in text.splitlines():
        if PLACEHOLDER in line:
            continue
        for m in re.finditer(r"\d[\d,\.]*\s?(?:대|명|분|개|%|초|건|행|곳|석|배|일|시간|KB|MB|ms)", line):
            a, b = max(0, m.start() - 28), min(len(line), m.end() + 12)
            snip = line[a:b].strip().strip("|").strip()
            key = m.group(0)
            if key not in seen and len(snip) > 4:
                seen.add(key)
                out.append(snip)
    return out[:25]


def collect_logs(root="logs", n=3):
    files = sorted(glob.glob(os.path.join(root, "*.log")), key=os.path.getmtime, reverse=True)[:n]
    out = []
    for p in files:
        lines = [l.strip() for l in _read(p).splitlines() if l.strip()]
        out.append((p, lines[-1][:110] if lines else ""))
    return out


# ----------------------------------------------------------------------------- 메인
def detect_project(explicit):
    if explicit:
        return explicit
    if os.path.isdir("app") or os.path.isdir("src"):
        return "."
    cands = [d for d in os.listdir(".") if os.path.isdir(d) and not d.startswith(".") and d not in SKIP_DIRS
             and (os.path.isdir(os.path.join(d, "app")) or os.path.exists(os.path.join(d, "src", "main.py")))]
    return cands[0] if len(cands) == 1 else "."


def find_doc(name, project):
    for p in (name, os.path.join(project, name)):
        if os.path.exists(p):
            return p
    return None


def main(argv):
    quiet = "-q" in argv
    project = None
    if "--project" in argv:
        i = argv.index("--project")
        project = argv[i + 1] if i + 1 < len(argv) else None
    project = detect_project(project)
    howto = find_doc("HOW_TO_RUN.md", project)
    aicol = find_doc("AI_COLLABORATION.md", project)
    if not howto:
        print("!! HOW_TO_RUN.md 를 작업 루트에도 %s/ 에도 찾지 못함" % project)
        return 2
    ht, at = _read(howto), _read(aicol) if aicol else ""

    print("== 확인 문제 훅 (%s) ==" % howto)
    bad = 0
    for name, st, n in hook_status(ht):
        ok = st == "채움"
        bad += 0 if ok else 1
        print("  [%s] %-22s %s" % ("OK " if ok else "NG ", name, st + ("" if ok else " ← 평가자가 이 자리를 질문으로 만든다")))
    ph_h, ph_a = placeholder_count(ht), placeholder_count(at)
    print("  [%s] (채움 남은 줄             HOW_TO_RUN %d · AI_COLLABORATION %d%s" % ("OK " if ph_h + ph_a == 0 else "NG ", ph_h, ph_a, "" if aicol else " (파일 없음)"))
    if aicol:
        for kw in ("받아들", "고치", "버린"):
            if kw not in at:
                print("  [-- ] AI_COLLABORATION 에 '%s' 표현 없음 — 수용/수정/폐기가 보이게" % kw)
    exists, nq, phq = quiz_status(os.path.join("docs", "QUIZ.md"))
    print("  [%s] docs/QUIZ.md                %s" % ("OK " if exists and nq >= 6 and phq == 0 else "-- ",
                                                      "답 %d개, (채움 %d — prompts/09-quiz.md 로 채운다" % (nq, phq) if exists else "없음 (setup.sh 가 docs/ 에 양식 설치)"))
    if quiet:
        return 1 if (bad or ph_h or ph_a) else 0

    # 재료
    lines = ["# QUIZ_CARD — 답에 쓸 식별자·숫자 (자동 수집, %s)" % project, "",
             "답마다 파일·테스트·숫자 1개 이상. 외울 것만 docs/QUIZ.md 암기 카드로 옮긴다.", ""]
    lines.append("## 파일 (머리말 요약)")
    for p in sorted(glob.glob(os.path.join(project, "app", "*.py")) + glob.glob(os.path.join(project, "tools", "*.py"))):
        d = first_docstring(p)
        if d:
            lines.append("- `%s` — %s" % (os.path.relpath(p, project), d))
    lines.append("")
    lines.append("## 테스트")
    tests = collect_tests(project)
    for f, name, doc in tests:
        lines.append("- `%s::%s`%s" % (f, name, (" — " + doc) if doc else ""))
    if not tests:
        lines.append("- (tests/ 에 test_*.py 없음)")
    lines.append("")
    routes = collect_routes(project)
    if routes:
        lines.append("## API")
        lines += ["- `%s`" % r for r in routes]
        lines.append("")
    env = collect_env(project)
    if env:
        lines.append("## 환경변수 (.env.example)")
        lines.append("- " + ", ".join("`%s`" % e for e in env))
        lines.append("")
    cmds = collect_commands(ht)
    if cmds:
        lines.append("## 명령 (HOW_TO_RUN)")
        lines += ["- `%s`" % c for c in cmds]
        lines.append("")
    nums = collect_numbers(ht + "\n" + at)
    lines.append("## 숫자 (문서에 쓴 값 — 로그로 뒷받침되는지 확인)")
    lines += ["- %s" % s for s in nums] or ["- (단위 붙은 숫자 없음 — 대표 결과·조건 변경 표에 측정값을 넣는다)"]
    lines.append("")
    logs = collect_logs()
    if logs:
        lines.append("## 최근 로그")
        lines += ["- `%s` — %s" % (p, last) for p, last in logs]
        lines.append("")
    lines.append("## 훅 상태")
    lines += ["- %s: %s" % (n, s) for n, s, _ in hook_status(ht)]
    os.makedirs("docs", exist_ok=True)
    out = os.path.join("docs", "QUIZ_CARD.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("== 재료: %s (파일 %d · 테스트 %d · API %d · 숫자 %d)" % (out, sum(1 for l in lines if l.startswith("- `") and ".py`" in l and "::" not in l), len(tests), len(routes), len(nums)))
    print("== 다음: 에이전트에 'hackathon-kit/prompts/09-quiz.md 를 읽고 수행해' → docs/QUIZ.md")
    return 1 if (bad or ph_h or ph_a) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
