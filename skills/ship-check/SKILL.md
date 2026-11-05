---
name: ship-check
description: 제출 20분 전, 배포 요건(환경변수·.env.example·DB 영속·헬스체크·Dockerfile·0.0.0.0/PORT)과 문서(실행 안내 양식·AI 협업 답변·README 원본 보존)·데이터셋 변형본·테스트 로그를 점검하고 빠진 것을 목록으로 돌려준다. "제출 전", "배포를 고려", "Dockerfile" 이 보이면 사용한다.
---

# ship-check

코드를 고치지 말고 점검 → 목록 → 사용자가 고를 수 있게.

## 1. 자동 점검
작업 루트에서 `python3 tools/preflight.py submit --project <이름>` 실행 결과를 그대로 붙인다 (NG 항목마다 고치는 데 몇 분 걸릴지).

## 2. 손 점검 (표로: 항목 | 상태 | 근거 파일:줄)
- 비밀값·포트·DB 경로가 환경변수인가, `.env.example` 에 전부 있나, 코드에 기본 비밀번호가 없나
- 빈 DB 로 시작 → 스키마 + 초기 데이터 자동 (server bootstrap)
- `/health` 가 DB 상태를 포함하나, 0.0.0.0 바인딩·PORT
- Dockerfile: COPY 대상에 kitlib/web/data 포함, pip 없음(또는 requirements 일치), CMD 가 실행 명령과 같음
- 실행 안내 문서: 과제 양식의 항목명·순서 그대로, 역할별 접속·데이터셋 준비/선택/적용/오류 확인·내보내기·설계 기준 포함, 비밀값 미기재
- AI 협업 답변: 세 질문 모두 사실(파일·숫자·테스트명)로, 빈 안내문 없음
- 루트 README 원본 그대로 (`docs/README_ORIGINAL.sha256`)
- 데이터셋 변형본: 정상 1 + 오류 3, NOTE.md, 생성 코드 포함
- 내보내기: 스키마 필드 전부, 파일 저장창 없음, `tools/verify_output.py` 통과
- 테스트: 실행 로그 경로, 실패 0, skip 사유
- 미구현·가정: 문서에 적혀 있나 (숨기지 않기)
- 확인 문제 준비: 실행 안내의 굵은 소제목 6개 채움(`(채움` 0), AI 협업 답변에 수용/수정/폐기·근거, `docs/QUIZ.md` 답 6개 — `python3 tools/quiz_prep.py --project <이름>` 결과

## 3. 출력
`지금 고치면 되는 것(≤5분) / 문서에 적고 넘어갈 것 / 손대지 말 것` 세 묶음.
