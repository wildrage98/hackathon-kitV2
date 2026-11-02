# HOW_TO_RUN

> 과제가 양식을 주면 **그 양식의 항목명·순서를 그대로** 쓴다. 아래는 기본 7항목.

## 1. 목적과 범위
(무엇을 만들었는지 / 다루는 문제와 업무 범위 / 다루지 않은 범위)

## 2. 기술 스택
Python 3.11 표준 라이브러리 (http.server, sqlite3, csv, json) + kitlib/ · 프런트: 프레임워크·CDN 없는 단일 페이지(inline SVG) · DB: SQLite · 컨테이너: Dockerfile

## 3. 준비 사항
- Python 3.11+ 또는 Docker. pip 설치 없음.
- 환경변수: `.env.example` → `.env` (필수: `ADMIN_PASSWORD`, `USER_PASSWORD`). 비밀값은 저장소에 없음.
- 데이터: `data/provided/`. 검증·시연용 데이터셋: `python3 tools/make_datasets.py` → `data/datasets/<이름>/` (NOTE.md 에 변경 내용)

## 4. 실행 방법
```bash
cp .env.example .env && bash run.sh                      # http://0.0.0.0:8000  (PORT 로 변경)
docker build -t __NAME__ . && docker run --rm -p 8000:8000 -e ADMIN_PASSWORD=... -e USER_PASSWORD=... -v __NAME__-data:/data __NAME__
```
헬스체크 `GET /health`. 빈 DB 로 시작하면 스키마 생성 후 `data/provided` 자동 적용.

## 5. 이용 순서와 대표 결과
- 역할별 접속: 운영자 `admin` / `ADMIN_PASSWORD` · 사용자 `<아이디>` / `USER_PASSWORD`
- 운영자: [데이터셋] 선택 → 검증(오류 행·열·코드 표시) → 적용(통과 시에만 교체, 실패 시 기존 유지) → [실행] 조건 입력·생성 → [결과] 확인 → [내보내기/검증]
- 적용 후 재생성 전에는 "이전 데이터 기준 — 재생성 필요"로 표시하고 사용자 화면은 결과를 보여주지 않음
- 사용자: 내 결과 조회
- 내보내기: 서버 `exports/` 저장 + 화면 표시·복사 (파일 선택창 없음)
- 대표 결과: (숫자로)
- 설계 기준·최적화 방식: (기준 우선순위 / 알고리즘 / 바꾸면 달라지는 지표)

## 6. 테스트
```bash
python3 -m unittest discover -s tests -v
```
(무엇을 확인하는지 — 경계값, 실패 경로, 전체 데이터 규칙 검증)

## 7. 가정과 제한 사항
(판단에 쓴 가정 — 누가 정한 값인지 / 알려진 제한 / 담당자 확인 필요 항목)
