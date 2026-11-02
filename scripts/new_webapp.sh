#!/usr/bin/env bash
# new_webapp.sh — 웹 서비스형 과제 뼈대를 **하위 폴더**에 생성 (작업 루트에서 실행). 이미 있는 폴더면 중단.
# 사용: bash tools/new_webapp.sh <이름> [--data <CSV폴더>]
# 결과: <이름>/{app/(config specs datasets store engine api server), web/, data/provided, data/datasets, tools/, tests/, kitlib/,
#              Dockerfile .env.example requirements.txt run.sh HOW_TO_RUN.md AI_COLLABORATION.md}
#   - 바로 실행 가능 (ADMIN_PASSWORD, USER_PASSWORD 만 있으면 로그인·데이터셋·실행·내보내기·헬스체크 동작)
#   - 채울 곳: app/specs.py (CSV 열 규칙·테이블), app/engine.py (run/view/user_view/verify), tools/make_datasets.py
set -euo pipefail
NAME="${1:-}"
[ -n "$NAME" ] || { echo "사용: bash tools/new_webapp.sh <이름> [--data <CSV폴더>]" >&2; exit 2; }
DATA=""
if [ "${2:-}" = "--data" ]; then DATA="${3:-}"; fi
ROOT="$(pwd)"
P="$ROOT/$NAME"
[ ! -e "$P" ] || { echo "[new_webapp] 이미 있음: $P" >&2; exit 1; }

SCAF=""
for c in "$ROOT/hackathon-kit/scaffold/webapp" "$ROOT/hackathon-kitV2/scaffold/webapp" "$(dirname "$0")/../scaffold/webapp" "$ROOT/scaffold/webapp"; do
  if [ -d "$c" ]; then SCAF="$c"; break; fi
done
[ -n "$SCAF" ] || { echo "[new_webapp] scaffold/webapp 을 찾지 못함 (hackathon-kit 이 작업 루트에 있어야 함)" >&2; exit 1; }

cp -r "$SCAF" "$P"
mkdir -p "$P"/data/provided "$P"/data/datasets "$P"/exports "$P"/logs "$P"/tools "$P"/tests
# kitlib 복사 (루트 → 프로젝트)
if [ -d "$ROOT/kitlib" ]; then cp -r "$ROOT/kitlib" "$P/kitlib";
elif [ -d "$ROOT/hackathon-kit/kitlib" ]; then cp -r "$ROOT/hackathon-kit/kitlib" "$P/kitlib";
elif [ -d "$ROOT/hackathon-kitV2/kitlib" ]; then cp -r "$ROOT/hackathon-kitV2/kitlib" "$P/kitlib";
else echo "[new_webapp] 경고: kitlib 없음 (setup.sh 먼저)" >&2; fi
find "$P" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
printf 'kitlib — 출처: https://github.com/wildrage98/hackathon-kitV2 (공개 저장소, MIT)\n사용한 모듈·수정 내용은 docs/DECISIONS.md 에 기록한다.\n' > "$P/kitlib/SOURCE.md" 2>/dev/null || true

# 이름 치환
grep -rl '__NAME__' "$P" --include='*.py' --include='*.html' --include='*.md' --include='*.example' --include='*.js' 2>/dev/null | while read -r f; do
  sed -i "s/__NAME__/${NAME}/g" "$f"
done

# 데이터 복사
if [ -n "$DATA" ] && [ -d "$DATA" ]; then
  cp "$DATA"/*.csv "$P/data/provided/" 2>/dev/null || true
  echo "[new_webapp] data/provided ← $DATA ($(ls "$P/data/provided" | grep -c csv || true)개 CSV)"
fi

echo "[new_webapp] 생성: ${NAME}/"
echo "  1) app/specs.py   — CSV 열 규칙(F/FileSpec)·TABLES·SCHEMA_SQL·USER_LOOKUP 을 과제 데이터로"
echo "  2) app/engine.py  — PARAMS, run(), view(), user_view(), verify()"
echo "  3) 실행: cd ${NAME} && ADMIN_PASSWORD=a USER_PASSWORD=u PORT=3000 python3 -m app.server   (터미널에서, 포트 미리보기)"
echo "  4) 테스트: cd ${NAME} && python3 -m unittest discover -s tests -v ; 데이터셋: python3 tools/make_datasets.py"
echo "  5) 제출 점검: python3 tools/preflight.py submit --project ${NAME}   (작업 루트에서)"
