# EXAM-DAY

처음이거나 서비스형이면 `playbook/RUNBOOK.md`(분 단위 순서표)를 따라간다. 아래는 요약.

## 0. 시작 (터미널)
```bash
git clone https://github.com/wildrage98/hackathon-kitV2.git hackathon-kit && bash hackathon-kit/setup.sh
python3 tools/preflight.py env
```
clone 불가 시: `hackathon-kitV2-main.zip` 업로드(uploads/) 후
```bash
mkdir -p /tmp/kit && (unzip -q uploads/hackathon-kit*.zip -d /tmp/kit || python3 -m zipfile -e uploads/hackathon-kit*.zip /tmp/kit)
mv "$(dirname "$(find /tmp/kit -maxdepth 2 -name setup.sh | head -1)")" hackathon-kit && bash hackathon-kit/setup.sh
python3 tools/preflight.py env
```
- `docs/TIMEBOX.md` 종료 시각, 제출 시작 시각(−10분; 확인 문제 30분이 시험 시간 안이면 −40분 — 안내문 확인)

## 1. 15분
1. README 정독 → `docs/SUBMIT_CHECK.md` (요구사항 번호 5개 이상이면 `docs/REQUIREMENTS.md` 도)
2. `playbook/README.md` §0 → 유형 → `0N-*.md` 질문 열기
3. 메신저: 질문 묶음 1 (`playbook/stakeholder-interview.md` §1) → `docs/QUESTIONS.md`
4. 데이터: `python3 tools/profile_csv.py <파일> --ts <시각> --key <키>` → 질문 묶음 2 (§2)
5. `docs/AGREEMENT.md` → 메신저 확인 → 시각 기록. 기준 없으면 §3 → 제안 → 확정

## 2. 에이전트 (터미널 탭 +)
```
AGENTS.md 와 hackathon-kit/prompts/00-kickoff.md 를 읽고 그 안의 지시를 그대로 수행해.
```
- 다음: `hackathon-kit/prompts/02-plan.md 를 읽고 수행해` → `$plan-verify` → 03 반복 → 04
- 승인: 파일·테스트 O / 서버·네트워크 X (내가 터미널에서)
- 지시 4요소: 목표 / 제약 / 완료 기준(명령+기대 출력) / 출력 형식

## 3. 30분까지 최소 실행본
- 분석·판정형(A~H):
```bash
bash tools/new_project.sh <이름>
cd <이름> && python3 src/main.py run && python3 -m unittest discover -s tests -v && cd ..
```
- 서비스형(I: 웹+역할+데이터셋+재계산+내보내기+Dockerfile) — `playbook/09-service.md`:
```bash
bash tools/new_webapp.sh <이름> --data <CSV폴더>
cd <이름> && ADMIN_PASSWORD=<값> USER_PASSWORD=<값> PORT=3000 python3 -m app.server     # 터미널, 포트 미리보기
```
  요구사항 번호 → `docs/REQUIREMENTS.md`(템플릿 `hackathon-kit/templates/REQUIREMENTS.md`). 에이전트: `$scaffold-web` → `$rule-check` → `$heuristic-opt` → 170분 `$ship-check`
- 지정 폴더가 있으면 그 폴더 + `cp -r kitlib <폴더>/`
- 서버: `cd <이름> && PORT=3000 python3 src/main.py serve` (터미널) → 포트 미리보기. 불가 → `dashboard_fallback` → outputs/*.html, README 명시
- 로그: `bash tools/run_and_log.sh run python3 <이름>/src/main.py run`

## 4. 커밋 (기능마다)
```bash
git add <이름> docs logs tools AGENTS.md .gitignore && git commit -m "feat: <무엇> — <기준>"
```
`git add -A` X

## 5. 100 / 130 / 150 / 165 / 174
- 100: 제출 가능? 아니면 TIMEBOX 축소 순서. 축소는 메신저 합의 + 기록
- 130: `python3 -m kitlib.synth` 또는 손 케이스 → `docs/VERIFICATION.md` (로그 경로)
- 150: 실행 안내 양식 그대로 + **굵은 소제목 6개**(구조 선택·모듈과 상태·잘못된 입력·설계 기준·조건을 바꾸면·검증함/가정함/미구현) 채움, AI 협업 답변(정책 이름 + 수용/수정/폐기 + 근거), `prompts/07`
- 165: `python3 tools/quiz_prep.py --project <이름>` → `hackathon-kit/prompts/09-quiz.md 를 읽고 수행해` → `docs/QUIZ.md` [근거 없음] 정리 → 암기 카드 2번
- 174: `python3 tools/preflight.py submit --project <이름>` → 커밋 → 제출

## 6. 제출 후 — 확인 문제 6문항 × 5분 (복사 불가, 평가 반영)
질문은 내 HOW_TO_RUN·AI_COLLABORATION 문장을 인용해 생성된다 → `docs/QUIZ.md` 의 답을 떠올려 쓴다.
문항마다 읽기 30초(유형 ①~⑥) → 뼈대 30초 → 타이핑 3분(500자, 첫 문장 결론, 식별자·숫자) → 검토 30초. `playbook/essay-prep.md`.

## X
- 메신저·에이전트에 외부 연결·저장소·과제 외 질문 X
- 한 줄 지시 X, 계획 없이 코딩 X, 질문 없이 기준 추측 X
- `git add -A` X, 루트 README 수정 X, 도구 업데이트 X, 지정 외 도구 X
- 다른 기기 X
