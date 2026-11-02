#!/usr/bin/env bash
# 로컬 실행: bash run.sh  (.env 가 있으면 읽는다)
set -e
cd "$(dirname "$0")"
[ -f .env ] && set -a && . ./.env && set +a
: "${ADMIN_PASSWORD:?ADMIN_PASSWORD 환경변수 필요 (.env.example)}"
: "${USER_PASSWORD:?USER_PASSWORD 환경변수 필요}"
exec python3 -m app.server
