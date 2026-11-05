#!/usr/bin/env python3
"""preflight.py — 환경 점검 + 제출 전 점검 (stdlib only, Python 3.8+).

  python3 tools/preflight.py env                       # 파이썬·패키지·소켓·쓰기권한·git
  python3 tools/preflight.py submit --project <폴더>    # 제출 10분 전: 필수 파일·로그 증거·비밀키·테스트 실행 여부·확인 문제 훅(서비스형)
  python3 tools/preflight.py all --project <폴더>

--project 를 생략하면 현재 폴더에 src/ 가 있으면 현재 폴더, 없으면 src/main.py 를 가진 하위 폴더가 하나뿐일 때 그 폴더.
docs/(DECISIONS, VERIFICATION)는 작업 루트 → 없으면 프로젝트 폴더에서 찾는다.
종료 코드: 0 = 점검한 항목 모두 OK / 1 = 문제 있음 / 2 = 점검한 항목이 없음(통과로 읽지 말 것)
출력은 logs/preflight_<시각>.log 에도 저장된다 (실행 증거).

숨김 폴더는 스캔하지 않는다.
"""
from __future__ import annotations

import importlib
import hashlib
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time

CHECKED = []   # (name, ok, detail)
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "hackathon-kit", "hackathon-kitV2"}


def check(name, ok, detail=""):
    CHECKED.append((name, bool(ok), detail))
    print("  [%s] %-28s %s" % ("OK " if ok else "NG ", name, detail))
    return ok


def warn(name, detail=""):
    print("  [-- ] %-28s %s" % (name, detail))


def _walk(top):
    """숨김 폴더·도구 폴더를 건너뛰는 os.walk"""
    for root, dirs, files in os.walk(top):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        yield root, dirs, files


def _run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:  # noqa: BLE001
        return -1, repr(e)


def env_checks():
    print("== 환경 점검 ==")
    v = sys.version_info
    check("python >= 3.8", v >= (3, 8), "%s (%s)" % (platform.python_version(), sys.executable))
    if v < (3, 11):
        warn("python < 3.11", "datetime.fromisoformat이 'Z'를 못 읽음 → kitlib.timeparse 사용")
    for mod in ("csv", "json", "sqlite3", "statistics", "http.server", "unittest", "argparse"):
        try:
            importlib.import_module(mod)
            ok = True
        except Exception:
            ok = False
        check("stdlib " + mod, ok)
    ext = {}
    import warnings
    for mod, dist in (("pandas", "pandas"), ("numpy", "numpy"), ("matplotlib", "matplotlib"), ("flask", "flask"), ("fastapi", "fastapi"),
                      ("uvicorn", "uvicorn"), ("streamlit", "streamlit"), ("sklearn", "scikit-learn"), ("pytest", "pytest"), ("requests", "requests")):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                importlib.import_module(mod)
            try:
                from importlib.metadata import version
                ext[mod] = version(dist)
            except Exception:
                ext[mod] = "?"
        except Exception:
            ext[mod] = None
    have = [k for k, x in ext.items() if x]
    warn("외부 패키지", "있음: %s / 없음: %s" % (", ".join("%s %s" % (k, ext[k]) for k in have) or "-", ", ".join(k for k, x in ext.items() if not x) or "-"))
    pip = shutil.which("pip") or shutil.which("pip3")
    warn("pip", pip or "없음 → stdlib만 사용")
    if pip:
        import tempfile
        try:
            with tempfile.TemporaryDirectory() as td:
                r = subprocess.run([sys.executable, "-m", "pip", "download", "-q", "--no-deps", "-d", td, "six==1.16.0"],
                                   capture_output=True, text=True, timeout=25)
            warn("pip 네트워크", "가능 (pip install 됨)" if r.returncode == 0 else "불가(또는 차단) → stdlib만: %s" % ((r.stderr.strip().splitlines() or [str(r.returncode)])[-1][:80]))
        except Exception as e:
            warn("pip 네트워크", "확인 실패(타임아웃 등): %r" % e)
    for tool in ("git", "node", "npm", "codex", "make", "sqlite3"):
        warn("cli " + tool, shutil.which(tool) or "없음")
    if shutil.which("codex"):
        rc, out = _run(["codex", "--version"], timeout=15)
        line = out.splitlines()[0] if out else "?"
        warn("codex 버전", line + ("" if "0.163" in line else "  (0.163 아님)"))
    # 서버 소켓
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", 0))
        s.listen(1)
        port = s.getsockname()[1]
        s.close()
        check("server socket bind 0.0.0.0", True, "가능 (임시 포트 %d)" % port)
    except OSError as e:
        check("server socket bind 0.0.0.0", False,
              "불가: %s → 터미널에서 직접 실행/승인 후 재시도, 안 되면 정적 HTML 폴백" % e)
    # 쓰기 권한
    try:
        p = ".preflight_write_test"
        with open(p, "w") as f:
            f.write("x")
        os.remove(p)
        check("cwd 쓰기 권한", True, os.getcwd())
    except Exception as e:
        check("cwd 쓰기 권한", False, repr(e))
    # 타임존/시각
    warn("현재 시각", time.strftime("%Y-%m-%d %H:%M:%S %Z") + " (TZ=%s)" % os.environ.get("TZ", "-"))
    # git
    if shutil.which("git"):
        rc, _ = _run(["git", "rev-parse", "--is-inside-work-tree"])
        if rc == 0:
            _, name = _run(["git", "config", "user.name"])
            _, email = _run(["git", "config", "user.email"])
            _, n = _run(["git", "rev-list", "--count", "HEAD"])
            warn("git repo", "예 (커밋 %s개). 신원: %s <%s>%s" % (n or "0", name or "?", email or "?",
                                                              "" if email else "  ← 커밋 전 git config user.name/email 필요"))
            if os.path.abspath(os.getcwd()) == os.path.abspath(os.path.expanduser("~")):
                warn("작업 루트 = 홈", "git add -A 금지 (캐시·도구 폴더가 딸려감) → git add <프로젝트폴더> docs logs")
        else:
            warn("git repo", "아니오 (git init 권장: 커밋 이력이 평가 자료)")
    # codex 설정 힌트
    codex_home = os.environ.get("CODEX_HOME", os.path.expanduser("~/.codex"))
    warn("CODEX_HOME", "%s (skills: %s)" % (codex_home, "있음" if os.path.isdir(os.path.join(codex_home, "skills")) else "없음"))
    for p in (".agents/skills", ".codex/skills"):
        if os.path.isdir(p):
            warn("repo skills", "%s: %s" % (p, ", ".join(sorted(os.listdir(p)))))


SECRET_PATTERNS = [
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI 키 형태"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"ghp_[A-Za-z0-9]{36}", "GitHub token"),
    (r"(?i)(api[_-]?key|secret|password|passwd)\s*[:=]\s*['\"][^'\"]{8,}['\"]", "하드코딩된 비밀값"),
]


def detect_project(explicit):
    if explicit:
        if not os.path.isdir(explicit):
            print("!! --project %s 폴더가 없습니다" % explicit)
            return None
        return explicit
    if os.path.isdir("src"):
        return "."
    cands = [d for d in os.listdir(".") if os.path.isdir(d) and not d.startswith(".") and d not in SKIP_DIRS
             and os.path.exists(os.path.join(d, "src", "main.py"))]
    if len(cands) == 1:
        print("  (프로젝트 폴더 자동 감지: %s/ — 다르면 --project 로 지정)" % cands[0])
        return cands[0]
    if cands:
        print("  (src/main.py 가 있는 폴더가 여럿: %s → --project 로 지정)" % ", ".join(cands))
    return "."


def submit_checks(project=None, required=("README.md",), test_cmd=None):
    print("== 제출 전 점검 ==")
    proj = detect_project(project)
    if proj is None:
        return
    pj = lambda *a: os.path.join(proj, *a)  # noqa: E731
    warn("프로젝트 폴더", os.path.abspath(proj))
    is_service = os.path.exists(pj("Dockerfile")) or os.path.isdir(pj("app")) or os.path.exists(pj("HOW_TO_RUN.md")) or os.path.exists("HOW_TO_RUN.md")
    for f in required:
        if f == "README.md" and is_service and (os.path.exists("HOW_TO_RUN.md") or os.path.exists(pj("HOW_TO_RUN.md"))):
            warn("프로젝트 README.md", "서비스형 — 실행 안내는 HOW_TO_RUN.md (루트 README 는 수정 금지)")
            continue
        check("필수 파일 " + pj(f), os.path.exists(pj(f)))
    # README에 실행 명령이 있나
    if os.path.exists(pj("README.md")):
        txt = open(pj("README.md"), encoding="utf-8", errors="ignore").read()
        check("README 실행 명령(python/bash)", bool(re.search(r"(python3?|bash|make|node|npm)\s+\S+", txt)), "실행 방법이 코드블록으로 있어야 함")
        check("README 미구현/미검증 섹션", bool(re.search(r"미구현|미검증|한계|Known|TODO|제한", txt)), "정직하게 적었는지")
    # 로그 증거 (프로젝트 logs/ + 루트 logs/)
    logs = []
    for ld in {pj("logs"), "logs"}:
        if os.path.isdir(ld):
            logs += [os.path.join(ld, f) for f in os.listdir(ld) if f.endswith(".log")]
    check("logs/ 실행 로그 존재", len(logs) > 0, "%d개" % len(logs))
    # docs: 루트 우선, 없으면 프로젝트 폴더
    def find_doc(name):
        for p in (os.path.join("docs", name), pj("docs", name)):
            if os.path.exists(p):
                return p
        return None
    vpath = find_doc("VERIFICATION.md")
    if vpath:
        txt = open(vpath, encoding="utf-8", errors="ignore").read()
        refs = re.findall(r"[\w./-]*logs/[\w./-]+\.log", txt)
        missing = [p for p in refs if not (os.path.exists(p) or os.path.exists(pj(p)))]
        check("VERIFICATION.md 로그 참조", len(refs) > 0 and not missing, "참조 %d개, 없는 파일 %s" % (len(refs), missing or "-"))
    else:
        warn("docs/VERIFICATION.md", "없음")
    dpath = find_doc("DECISIONS.md")
    if dpath:
        n = len(re.findall(r"^- \[\d{1,2}:\d{2}\]", open(dpath, encoding="utf-8", errors="ignore").read(), re.M))
        check("DECISIONS.md 기록 줄", n >= 3, "%d줄" % n)
    # 비밀키 스캔 (프로젝트 + 루트 docs/tools, 숨김 폴더 제외)
    scanned, found = 0, []
    roots = [proj] + ([d for d in ("docs", "tools") if proj != "." and os.path.isdir(d)])
    for top in roots:
        for root, dirs, files in _walk(top):
            for fn in files:
                if fn.endswith((".py", ".md", ".json", ".txt", ".yaml", ".yml", ".toml", ".env", ".sh", ".js", ".html", ".cfg", ".ini", ".csv")):
                    p = os.path.join(root, fn)
                    try:
                        if os.path.getsize(p) > 2_000_000:
                            continue
                        txt = open(p, encoding="utf-8", errors="ignore").read()
                    except Exception:
                        continue
                    scanned += 1
                    for pat, label in SECRET_PATTERNS:
                        if re.search(pat, txt):
                            found.append("%s (%s)" % (p, label))
    if scanned == 0:
        warn("비밀키 스캔", "스캔한 파일 없음 (SKIP)")
    else:
        check("비밀키 없음 (%d 파일 스캔)" % scanned, not found, "; ".join(found[:5]))
    # 테스트 실행 (프로젝트 폴더에서)
    tests_dir = pj("tests")
    cmd = test_cmd or ([sys.executable, "-m", "pytest", "-q", "tests"] if os.path.isdir(tests_dir) and shutil.which("pytest") else
                       [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"] if os.path.isdir(tests_dir) else None)
    if cmd:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=proj)
        tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]
        check("tests 실행 (%s)" % " ".join(cmd[1:]), r.returncode == 0, tail[0][:100])
    else:
        warn("tests/", "없음 — 최소 1개 테스트 권장")
    # 서비스형 (웹 서비스) 제출물: Dockerfile / .env.example / HOW_TO_RUN / AI_COLLABORATION / 루트 README 보존 / 데이터셋 변형본
    if is_service:
        def _any(*paths):
            return next((x for x in paths if os.path.exists(x)), None)
        check("Dockerfile", bool(_any(pj("Dockerfile"), "Dockerfile")))
        check(".env.example", bool(_any(pj(".env.example"), ".env.example")))
        gi = open(pj(".gitignore"), encoding="utf-8", errors="ignore").read() if os.path.exists(pj(".gitignore")) else ""
        check(".env 미포함", (not os.path.exists(pj(".env"))) or (".env" in gi), "비밀값 파일은 .gitignore")
        for name in ("HOW_TO_RUN.md", "AI_COLLABORATION.md"):
            path = _any(name, pj(name))
            if not path:
                check(name, False, "작업 루트에 있어야 함 (과제 양식)")
                continue
            txt = open(path, encoding="utf-8", errors="ignore").read()
            blanks = re.findall(r"^\((?:답변|무엇을|사용한|필요한|실행|기본|테스트|판단|현상|경계값|AI 첫)[^\n]*\)$", txt, re.M)
            n_blank = len(blanks) + txt.count("(채움")
            check("%s 양식 빈칸 없음" % name, n_blank == 0, "남은 안내문·(채움 %d개" % n_blank)
            if name == "HOW_TO_RUN.md":
                check("HOW_TO_RUN 실행 명령", bool(re.search(r"(python3?|bash|docker|npm|node)\s+\S+", txt)))
                # 확인 문제(제출 후 6문항) 출처가 되는 굵은 소제목 6개 — tools/quiz_prep.py 와 같은 판정
                try:
                    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                    import quiz_prep  # noqa: E402
                    hs = quiz_prep.hook_status(txt)
                    missing = [n for n, st, _ in hs if st != "채움"]
                    check("HOW_TO_RUN 확인 문제 훅 6개", not missing, ("비어 있음: " + ", ".join(missing)) if missing else "구조 선택·모듈과 상태·잘못된 입력·설계 기준·조건을 바꾸면·검증함/가정함/미구현")
                except Exception as e:  # noqa: BLE001
                    warn("확인 문제 훅", "quiz_prep.py 없음 (%r)" % e)
        qz = os.path.join("docs", "QUIZ.md")
        if os.path.exists(qz):
            qt = open(qz, encoding="utf-8", errors="ignore").read()
            nq, nph = len(re.findall(r"^## Q\d", qt, re.M)), qt.count("(채움")
            check("확인 문제 답안 docs/QUIZ.md", nq >= 6 and nph == 0, "답 %d개, (채움 %d — prompts/09-quiz.md" % (nq, nph))
        else:
            warn("docs/QUIZ.md", "없음 — 제출 후 확인 문제 6문항 대비 (tools/quiz_prep.py → prompts/09-quiz.md)")
        if os.path.exists("docs/README_ORIGINAL.sha256") and os.path.exists("README.md"):
            want = open("docs/README_ORIGINAL.sha256", encoding="utf-8").read().split()[0]
            got = hashlib.sha256(open("README.md", "rb").read()).hexdigest()
            check("루트 README.md 원본 보존", want == got, "수정됨 — 과제 지시문은 건드리지 않는다" if want != got else "")
        ds = pj("data", "datasets")
        n_ds = len([d for d in os.listdir(ds) if os.path.isdir(os.path.join(ds, d))]) if os.path.isdir(ds) else 0
        check("데이터셋 변형본 (정상·오류) 준비", n_ds >= 2, "%d개 (tools/make_datasets.py)" % n_ds)
        hp = _any(pj("app", "api.py"), pj("src", "main.py"), pj("server.py"), pj("app.py"))
        if hp:
            code = open(hp, encoding="utf-8", errors="ignore").read()
            check("/health 엔드포인트", "/health" in code)
            check("0.0.0.0 바인딩/PORT 환경변수", ("0.0.0.0" in code or "HOST" in code) and "PORT" in code or os.path.exists(pj("app", "config.py")))
    # 대용량
    big = []
    for root, dirs, files in _walk(proj):
        for fn in files:
            p = os.path.join(root, fn)
            try:
                if os.path.getsize(p) > 50_000_000:
                    big.append(p)
            except OSError:
                pass
    check("50MB 초과 파일 없음", not big, ", ".join(big[:3]))
    # git 상태 힌트
    if shutil.which("git"):
        rc, out = _run(["git", "status", "--porcelain", "--", proj if proj != "." else "."])
        if rc == 0:
            n = len([l for l in out.splitlines() if l.strip()])
            warn("git 미커밋 변경", "%d개 → 제출 전 커밋 (git add %s docs logs tools && git commit)" % (n, proj))


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    mode = args[0] if args else "all"
    project = None
    if "--project" in argv:
        i = argv.index("--project")
        project = argv[i + 1] if i + 1 < len(argv) else None
    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", "preflight_%s.log" % time.strftime("%Y%m%d_%H%M%S"))

    class Tee:
        def __init__(self, f):
            self.f, self.o = f, sys.stdout

        def write(self, s):
            self.f.write(s); self.o.write(s)

        def flush(self):
            self.f.flush(); self.o.flush()

    with open(log_path, "w", encoding="utf-8") as f:
        sys.stdout = Tee(f)
        try:
            if mode in ("env", "all"):
                env_checks()
            if mode in ("submit", "all"):
                submit_checks(project)
            n_ng = sum(1 for _, ok, _ in CHECKED if not ok)
            print("== 결과: 점검 %d개, 실패 %d개 → %s" % (len(CHECKED), n_ng, log_path))
        finally:
            sys.stdout = sys.__stdout__
    if not CHECKED:
        print("!! 점검한 항목이 없습니다. 통과로 읽지 마세요. (exit 2)")
        return 2
    return 1 if n_ng else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
