# hackathon-kit

개인 작업 하네스. 문제 풀이 코드 없음 — 절차 양식, 점검 도구, stdlib 전용 빌딩블록, 체크리스트.

```bash
git clone https://github.com/wildrage98/hackathon-kitV2.git hackathon-kit && bash hackathon-kit/setup.sh
python3 tools/preflight.py env
bash tools/new_project.sh <이름>                     # 분석·판정형
bash tools/new_webapp.sh <이름> --data <CSV폴더>       # 서비스형 (웹+역할+데이터셋+재계산+내보내기+Dockerfile)
```

```
EXAM-DAY.md          순서표
AGENTS.md            에이전트 작업 규칙
setup.sh             설치 (AGENTS.md, skills/, kitlib/, templates→docs/, scripts→tools/, .gitignore)
kitlib/              stdlib 전용 모듈 24개 (각 파일 머리말에 API)
scaffold/webapp/     서비스형 뼈대 (new_webapp.sh 가 복사: 로그인·역할·데이터셋 검증/적용·실행·결과·내보내기·헬스체크·Dockerfile)
playbook/            유형별 체크리스트 01~09, 인터뷰, 질문 목록, 에이전트 운용
prompts/             단계별 프롬프트 00~08
examples/            배선 예시 2개 (참고용)
templates/           docs/ 양식 8개
scripts/             preflight, profile_csv, new_project, new_webapp, run_and_log, smoke
skills/              plan-verify, decision-log, scaffold-web, rule-check, heuristic-opt, ship-check
tests/               kitlib 테스트 (python -m unittest discover -s tests)
```

```python
from kitlib import csvio, timeparse, quality, rules, alerts, report
rows, meta = csvio.read_csv("data/x.csv")
timeparse.add_parsed_time(rows, "timestamp")
q = quality.check_quality(rows, key_cols=["equipment"], value_cols=["temp"])
clean, log = quality.apply_policy(rows, q["issues"], key_cols=["equipment"], value_cols=["temp"])
rules.evaluate_series(clean, [rules.Rule("temp_hi", "temp", hi=70, when={"state": "RUN"}, min_consecutive=2)], key_cols=["equipment"])
am = alerts.run_from_levels(clean, ["equipment"], close_after=6)
report.Report("리포트").table(am.to_rows()).save_html("outputs/report.html")
```

- 공개 유지. 완성 코드 없음. clone만 한다 (push·외부 전송 없음).
- MIT
