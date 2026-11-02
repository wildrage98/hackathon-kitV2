# 표준 라이브러리만 사용 → pip 없음, 오프라인 빌드 가능
FROM python:3.11-slim
WORKDIR /app
COPY app ./app
COPY kitlib ./kitlib
COPY web ./web
COPY data/provided ./data/provided
COPY data/datasets ./data/datasets
COPY tools ./tools
COPY HOW_TO_RUN.md ./
ENV PYTHONUNBUFFERED=1 HOST=0.0.0.0 PORT=8000 DB_PATH=/data/app.db EXPORT_DIR=/data/exports
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python3 -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8000'), timeout=4).status==200 else 1)"
CMD ["python3", "-m", "app.server"]
