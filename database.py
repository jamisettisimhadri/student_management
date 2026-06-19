import os

try:
    import pymysql
except ModuleNotFoundError:
    pymysql = None

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "fastapi_db")

base_dir = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB_PATH = os.path.join(base_dir, "app.db")


def _create_mysql_engine():
    if pymysql is None:
        raise RuntimeError("pymysql is not installed")

    conn = pymysql.connect(host=DB_HOST, port=int(DB_PORT), user=DB_USER, password=DB_PASS)
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    conn.commit()
    conn.close()

    if DB_PASS:
        database_url = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        database_url = f"mysql+pymysql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    return create_engine(database_url)


try:
    engine = _create_mysql_engine()
    print("Database check complete.")
except Exception as exc:
    print(f"MySQL unavailable, using SQLite fallback: {exc}")
    engine = create_engine(
        f"sqlite:///{SQLITE_DB_PATH}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
