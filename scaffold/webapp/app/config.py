"""환경변수 설정. 비밀값은 코드에 두지 않는다 (.env.example)."""
import os


def _env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_NAME = _env("APP_NAME", "__NAME__")
HOST = _env("HOST", "0.0.0.0")
PORT = int(_env("PORT", "8000"))
DB_PATH = _env("DB_PATH", os.path.join(BASE_DIR, "data", "app.db"))
DATA_DIR = _env("DATA_DIR", os.path.join(BASE_DIR, "data"))
PROVIDED_DIR = os.path.join(DATA_DIR, "provided")
DATASETS_DIR = os.path.join(DATA_DIR, "datasets")
EXPORT_DIR = _env("EXPORT_DIR", os.path.join(BASE_DIR, "exports"))
WEB_DIR = os.path.join(BASE_DIR, "web")

ADMIN_USER = _env("ADMIN_USER", "admin")
ADMIN_PASSWORD = _env("ADMIN_PASSWORD")      # 운영자. 없으면 기동 시 경고
USER_PASSWORD = _env("USER_PASSWORD")        # 일반 사용자 공통 비밀번호 (아이디는 specs.USER_LOOKUP 으로 확인)
SECRET_KEY = _env("SECRET_KEY", "dev-only-change-me")
SESSION_TTL_MIN = int(_env("SESSION_TTL_MIN", "480"))
