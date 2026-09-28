from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from . import config

SQLALCHEMY_DATABASE_URL = config.DATABASE_URL
_eh_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if _eh_sqlite else {},
)

if _eh_sqlite:
    @event.listens_for(engine, "connect")
    def _configurar_sqlite(conexao_dbapi, _):
        # WAL permite várias leituras simultâneas durante uma escrita: essencial com vários
        # celulares/usuários acessando ao mesmo tempo. busy_timeout evita "database is locked".
        cursor = conexao_dbapi.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
