# RUNBOOK — 서비스형 과제를 내가 푸는 순서 (180분 + 확인 문제 30분)

이 파일 하나만 보고 따라간다. 각 줄 = `시각 | 할 일 | 명령 또는 타이핑 | 산출물 | 완료 기준`.
확인 문제(6문항 × 5분)가 3시간 **안에** 포함이면 100분 이후 시각을 전부 **−30분**. 안내문 첫 줄에서 확인한다.
축소 순서(100분 체크포인트에서 시간 부족 시): 사용자 화면 그래프 → 비교 실험 → 데이터셋 변형본 수 → 내보내기 CLI. **절대 안 버리는 것**: 규칙 검증기, 오류본 거부, stale, 실행 안내 양식, 확인 문제 훅 6개.

## 0–15 시작 · 파악 · 질문
| 시각 | 할 일 | 명령 / 타이핑 | 산출물 | 완료 기준 |
|---|---|---|---|---|
| 0 | 설치 | `git clone https://github.com/wildrage98/hackathon-kitV2.git hackathon-kit && bash hackathon-kit/setup.sh` → `python3 tools/preflight.py env` | tools/ docs/ kitlib/ | 실패 0 |
| 2 | 시각 | docs/TIMEBOX.md: 종료, 제출 시작(= 종료 −10, 확인 문제 포함이면 −40) | TIMEBOX | 두 시각 적힘 |
| 2–10 | README 정독 (내가) | 요구사항 번호 세기, "해야 합니다" 문장 표시, 필수 산출물·양식 이름 → docs/SUBMIT_CHECK.md. **루트 README 는 절대 수정 안 함** | SUBMIT_CHECK | 산출물 표 채움 |
| 5 | 메신저 묶음 1 | `playbook/stakeholder-interview.md` §1 그대로 + `09-service.md` 질문(운영·시간 기준·편의 숫자·효율 우선순위) 3개 | — | 전송됨 |
| 8 | 데이터 훑기 | `python3 tools/profile_csv.py data/<파일>.csv` × 핵심 2개 | — | 행 수·키·결측 파악 |
| 10 | 에이전트 시작 (터미널 탭 +) | `AGENTS.md 와 hackathon-kit/prompts/00-kickoff.md 를 읽고 그 안의 지시를 그대로 수행해.` | docs/REQUIREMENTS.md (서비스형이면 자동), 질문 5개 | 표·질문 받음 → 묶음 2 전송 |
| 12 | 뼈대 | `bash tools/new_webapp.sh <이름> --data data` → `cd <이름> && ADMIN_PASSWORD=<값> USER_PASSWORD=<값> PORT=<지정 포트> python3 -m app.server` (이 터미널은 끝까지 유지) | <이름>/ | 포트 미리보기에서 로그인·데이터셋·/health |
| 14 | 양식 위치 | 과제가 루트를 지정하면 `cp <이름>/HOW_TO_RUN.md <이름>/AI_COLLABORATION.md .` — 이후 편집은 **루트 파일**에서, 제출 직전 `cp HOW_TO_RUN.md <이름>/` (Dockerfile 이 COPY 하므로 둘을 같게) | 루트 문서 | preflight·quiz_prep 가 루트를 먼저 읽음 |

## 15–30 기준 확정 · 계획 · 첫 파일
| 시각 | 할 일 | 명령 / 타이핑 | 산출물 | 완료 기준 |
|---|---|---|---|---|
| 15 | 답 정리 | 메신저 답 → docs/QUESTIONS.md 확정 메모 표. 없다는 기준은 "X로 가정하고 화면에서 바꿀 수 있게 두겠습니다" 제안 → 확정 | QUESTIONS | 숫자 기준 전부 출처 표시 |
| 20 | 합의서 | docs/AGREEMENT.md 초안 → 메신저로 확인 → 시각 기록 | AGREEMENT | "맞습니다" 받음 |
| 22 | 계획 | 에이전트: `계획 시작` → `$plan-verify` → docs/PLAN.md → 내가 `계획 승인` | PLAN | 개발 순서 표에 완료 기준 있음 |
| 25 | 훅 ① 초안 | HOW_TO_RUN §2 **구조 선택** 3줄: 결정 / 대안 2개와 버린 이유 / 제약. 지금 결정했으니 지금 적는다 (예: 생성 N초 → 동기. 큐+worker 는 복구·동시성 때문에 X) | HOW_TO_RUN | `(채움` 1개 줄어듦 |
| 25 | specs | 에이전트: `$scaffold-web 로 app/specs.py 부터. CSV 마다 FileSpec(타입·unique·ref), TABLES, SCHEMA_SQL, USER_LOOKUP.` | app/specs.py | 데이터셋 화면에서 provided 검증 통과, 행 수 표시 |
| 28 | 커밋 | `git add <이름> docs logs tools AGENTS.md .gitignore && git commit -m "feat: specs — 7종 검증"` | — | `git add -A` 금지 |

## 30–60 최소 실행본 (규칙만 지키는 가장 단순한 답)
| 시각 | 할 일 | 명령 / 타이핑 | 산출물 | 완료 기준 |
|---|---|---|---|---|
| 30 | 검증기 먼저 | 에이전트: `$rule-check — README 규칙 문장을 표로 뽑고 engine.verify() 를 규칙마다 한 블록으로. 생성 코드 쓰지 말고 결과+입력만. mutate_check 로 일부러 깨뜨린 결과가 잡히는지 테스트.` | engine.verify, tests | 깨뜨린 케이스 전부 잡힘 |
| 40 | 가장 단순한 생성 | 에이전트: `engine.run() — 규칙만 지키는 가장 단순한 답(예: 수요 많은 순 greedy, 정원 분리, 직행). 최적화 금지. view() 에 지표 3개.` | engine.run | 실행 탭 "규칙 검증 통과" 배지 |
| 50 | 사용자 화면 | `user_view() — 내 배정·내 결과·시간표. USER_LOOKUP 으로 아이디 확인.` | user_view | 사용자 로그인 → 내 결과 |
| 55 | 훅 ② | HOW_TO_RUN §2 **모듈과 상태** 표의 `(채움` 칸 채움 (run 순서 한 줄) | HOW_TO_RUN | 표 완성 |
| 58 | 커밋 + 메신저 중간 보고 | `tools/run_and_log.sh test python3 -m unittest discover -s tests -v` → 커밋 → "1) 2) 동작, 3) 진행 중, 확인 1개" | logs/ | 로그 파일 있음 |

## 60–100 계산 품질 (기준 하나씩)
| 시각 | 할 일 | 명령 / 타이핑 | 산출물 | 완료 기준 |
|---|---|---|---|---|
| 60 | 기준 우선순위 | docs/DECISIONS.md 에 한 줄: "규칙 > 접근(한도 2단계) > 우회 한도 > 자원 수 > 시간" (담당자 확인값 / 개발자 가정 구분) | DECISIONS | 숫자 전부 PARAMS |
| 62 | 기준 반영 | 에이전트: `$heuristic-opt — PARAMS 로 노출된 기준을 run() 에 하나씩. 매 기능마다 verify 결과와 지표(자원 수·사용률·평균/최대 시간·한도 초과 0) 보고.` | engine.run | 위반 0 유지 |
| 80 | 현실성 점검 | 자원 수가 현행 2배 초과 또는 사용률 < 30% → 원인 후보 3개(비율 한도 → +분 병행 / 선택 규칙 최근접 / 소규모 통합) → 비교 실험 `tools/experiment_*.py` 3~5개 × 지표 표 | 비교 표 | 숫자로 선택 |
| 90 | 훅 ⑤ 측정 | 비교 표에서 2행(기본 / 정원 축소 등) + 생성 시간(로그 타임스탬프) + 병목 한 줄 → HOW_TO_RUN **조건을 바꾸면** | HOW_TO_RUN | 측정값 2행 |
| 95 | 커밋 | 기능마다 커밋, DECISIONS 1줄 | — | — |

## 100 체크포인트
| 시각 | 할 일 | 명령 / 타이핑 | 산출물 | 완료 기준 |
|---|---|---|---|---|
| 100 | 제출 가능? | docs/REQUIREMENTS.md 상태 열 전부 채움 → × 행부터. 부족하면 축소 순서대로 빼고 **메신저 합의 + DECISIONS 기록** | REQUIREMENTS | 지금 제출해도 0점 항목 없음 |

## 100–130 데이터 관리 · 내보내기 · 실패 경로
| 시각 | 할 일 | 명령 / 타이핑 | 산출물 | 완료 기준 |
|---|---|---|---|---|
| 100 | 내보내기 | 과제 스키마 필드 전부 → `/api/result/export` + `tools/verify_output.py` 로 파일 기준 재검증 | exports/ | CLI 통과 |
| 110 | 변형본 | `python3 tools/make_datasets.py` → 정상 변경본 1(근무표·상태 변경) + 오류본 3(필수 열 누락 / 참조 오류 / 형식 오류), NOTE.md 첫 줄 | data/datasets/ | 화면에서 오류본 거부 + 배지 유지, 변경본 적용 → stale → 재생성 → 숫자 달라짐 |
| 120 | 실행 중 재요청 | 결정하고 구현: 실행 중이면 409 (큐잉 안 함) 또는 대기 — 하나만 | api | 동작 확인 |
| 125 | 훅 ④ | HOW_TO_RUN §5 **잘못된 입력·어긋난 순서** 표 3행 완성 (코드 위치·HTTP 상태) | HOW_TO_RUN | `(채움` 0 |
| 128 | 테스트 | tests/test_api.py 에 오류본 거부·stale·재생성 반영 추가 → run_and_log | logs/ | 통과 로그 |

## 130–150 검증 · 배포 요건
| 시각 | 할 일 | 명령 / 타이핑 | 산출물 | 완료 기준 |
|---|---|---|---|---|
| 130 | 전체 데이터 재검사 | `tools/run_and_log.sh check python3 tools/verify_output.py exports/<파일>.json` + 경계값 테스트(정원과 같을 때, 기한과 같을 때, 자정 넘김, 휴무자) | logs/, tests | 위반 0, 로그 경로 |
| 138 | VERIFICATION | docs/VERIFICATION.md — 요구사항별 입력·기대·실제·로그 경로. 안 한 건 "미검증" | VERIFICATION | 로그 없는 "통과" 없음 |
| 142 | 배포 요건 | `.env.example` 전부, 비밀값 코드에 없음, `/health` 에 DB 상태, 0.0.0.0/PORT, Docker 가능하면 `docker build -t <이름> .` (안 되면 "미검증"으로) | — | preflight 서비스형 항목 OK |
| 146 | 훅 ③ | HOW_TO_RUN §6 **검증함 / 가정함 / 미구현** 표 (테스트명·로그·PARAMS·§7) | HOW_TO_RUN | 3구분 각 1행 이상 |

## 150–165 문서 (여기서 확인 문제가 결정된다)
| 시각 | 할 일 | 명령 / 타이핑 | 산출물 | 완료 기준 |
|---|---|---|---|---|
| 150 | HOW_TO_RUN 완성 | 과제 양식 항목명·순서 그대로. **대표 결과**(숫자), **설계 기준**(우선순위·알고리즘 한 줄·PARAMS), §7 가정(누가 정한 값) | HOW_TO_RUN | `python3 tools/quiz_prep.py --project <이름>` → 훅 6개 OK, `(채움` 0 |
| 156 | AI_COLLABORATION (훅 ⑥) | Q1~Q3 각각: 정책 이름 → AI 첫 결과 숫자 → 내가 본 문제 → 지시한 수정(코드 위치) → 결과 숫자 → 테스트명. 받아들인 것/고치게 한 것/버린 것 각 1개 이상 | AI_COLLABORATION | `(채움` 0 |
| 160 | 약점 | 에이전트: `hackathon-kit/prompts/07-self-critique.md 를 읽고 수행해` → DECISIONS 자가 진단 | DECISIONS | Top 5 |
| 163 | 커밋 | 경로 지정 커밋 | — | — |

## 165–180 확인 문제 준비 · 제출
| 시각 | 할 일 | 명령 / 타이핑 | 산출물 | 완료 기준 |
|---|---|---|---|---|
| 165 | 재료 + 답 초안 | `python3 tools/quiz_prep.py --project <이름>` → 에이전트: `hackathon-kit/prompts/09-quiz.md 를 읽고 수행해` (`$quiz-prep`) | docs/QUIZ_CARD.md, docs/QUIZ.md | [근거 없음] 0 (있으면 문서 고치거나 답에서 뺌) |
| 170 | 외우기 | QUIZ.md 답 6개 소리 내어 1번, 암기 카드(파일 5·테스트 5·숫자 5·명령 3·한계 3) 2번 | — | 식별자가 입에 붙음 |
| 174 | 최종 점검 | `python3 tools/preflight.py submit --project <이름>` → NG 는 5분 안에 고칠 것만 → 커밋 | logs/preflight_*.log | 실패 0 또는 문서에 명시 |
| 177 | 제출 | 에디터 저장 상태 확인 → 제출 → 미리보기 → 확정 | — | — |
| 제출 후 | 확인 문제 6개 | 문항마다: 30초 읽기(유형 ①~⑥ 판별) → 30초 뼈대(결론/근거/대안/한계) → 3분 타이핑(500자, 첫 문장 결론, 식별자·숫자) → 30초 검토. 모르면 "검증 못 했다 + 검증하려면 X" | — | 6/6 제출 |

## 내가 쓰는 풀이 원칙 (왜 이 순서인가)
1. **검증기를 생성기보다 먼저.** 규칙은 채점 기준이고, 생성 코드가 틀려도 검증기가 잡으면 제출물은 산다. 둘을 분리해야 "AI 설명에 의존하지 않는 확인"이 된다.
2. **규칙만 지키는 가장 단순한 답 → 기준을 하나씩.** 최적해를 찾지 않는다. 기준은 PARAMS 로 빼고 지표 표로 비교한다. 첫 결과가 비현실적이면(자원 2배·사용률 30% 미만) 알고리즘이 아니라 기준을 의심한다.
3. **실패 경로를 기능으로 취급.** 오류본 거부·기존 유지·stale·실행 중 재요청은 요구사항이고 확인 문제 ④의 원문이다. 테스트로 고정한다.
4. **문서는 질문의 출처.** 굵은 소제목 6개는 "내가 받고 싶은 질문" 이다. 방어할 수 있는 결정·숫자·테스트명만 쓴다. AI 가 만든 구조를 내가 설명 못 하면 단순화한다.
5. **숫자는 로그에서.** 문서의 모든 숫자(시간·건수·%)는 logs/ 또는 테스트 출력에 있어야 한다. 없으면 쓰지 않는다.
6. **100분에 제출 가능 상태.** 그 뒤는 더하는 것이지 고치는 것이 아니다.
