from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import DB_PATH
from .crypto import EncryptedString

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False, unique=True)
    kaggle_username = Column(String(128), nullable=False)
    kaggle_api_key = Column(EncryptedString(512), nullable=False)
    kernel_slug = Column(String(256), nullable=False)
    tunnel_token = Column(EncryptedString(4096), nullable=False)
    tunnel_url = Column(String(512), nullable=False, default="")
    last_status = Column(String(32), nullable=False, default="unknown")
    last_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
