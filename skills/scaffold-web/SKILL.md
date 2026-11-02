---
name: scaffold-web
description: 웹 서비스형 과제(역할·데이터셋 선택/검증/적용·재계산·내보내기·DB·헬스체크·Dockerfile)의 뼈대를 tools/new_webapp.sh 로 만들고 specs.py/engine.py 를 채워 요구사항을 하나씩 붙인다. "웹 서비스", "운영자/구성원", "데이터셋 적용", "Dockerfile" 이 보이면 사용한다.
---

# scaffold-web

## 0. 뼈대 (코드 작성 전)
1. 작업 루트에서 `bash tools/new_webapp.sh <이름> --data <제공 CSV 폴더>` 실행. 이미 있으면 건너뛴다.
2. 사용자에게 터미널에서 `cd <이름> && ADMIN_PASSWORD=... USER_PASSWORD=... PORT=3000 python3 -m app.server` 를 실행해 달라고 요청한다 (네가 서버를 띄우지 않는다). `/health` 가 200 이면 시작.
3. `docs/REQUIREMENTS.md` 에 요구사항 번호마다 1행을 만든다. 이후 모든 작업은 행 번호를 달고 한다.

## 1. 채우는 순서 (파일 3개만 만진다)
1. `app/specs.py` — 제공 CSV 마다 `FileSpec`: 열 타입, `unique`/`pk`, 파일 간 `ref`. `TABLES`·`SCHEMA_SQL` 을 같은 열로. 사용자 로그인 아이디가 있는 테이블은 `USER_LOOKUP`.
   확인: 데이터셋 화면에서 provided 검증 통과·행 수 표시. `tools/make_datasets.py` 로 오류본을 만들어 거부되는지.
2. `app/engine.py` — `PARAMS`(운영 조건·판단 기준 숫자 전부), `verify()`(규칙마다 한 블록, 생성 코드와 독립), `run()`(규칙만 지키는 가장 단순한 답 → 이후 개선), `view()`/`user_view()`(뷰 스펙: metrics·tables·graph·timeline).
   확인: 실행 탭에서 생성 → "규칙 검증 통과" 배지. 사용자 로그인 → 내 결과.
3. `tools/make_datasets.py` — 정상 변경본 1개 이상(근무표·상태 변경), 오류본(필수 열 누락 / 참조 오류 / 형식 오류) 각 1개. NOTE.md 첫 줄에 무엇이 달라졌는지.

## 2. 지키는 것
- 루트 README 수정 금지. 실행 안내는 과제가 지정한 파일(예: HOW_TO_RUN.md)의 양식 그대로.
- 숫자 기준은 코드에 박지 않는다 → PARAMS 또는 환경변수. 문서에 "담당자 확인값 / 개발자 가정"을 구분해 적는다.
- 데이터셋 적용 후 재생성 전에는 결과를 새 데이터 결과로 보여주지 않는다 (scaffold 의 stale 처리 유지).
- 파일 업로드·파일 저장창을 여는 기능을 만들지 않는다. 서버 폴더 선택 / 서버 폴더 저장 + 화면 표시.
- 외부 패키지·CDN 없이 간다. 꼭 필요하면 사용자에게 먼저 묻고 requirements.txt 와 Dockerfile 을 같이 고친다.
- 서버 실행·curl·docker build 는 사용자가 터미널에서 한다. 너는 결과 파일·테스트로 확인한다.

## 3. 끝낼 때
- `python3 -m unittest discover -s tests -v` 로그 경로 보고 → `docs/VERIFICATION.md`
- REQUIREMENTS.md 상태 열 갱신 → × 남은 행을 사용자에게 보고 (숨기지 않는다)
