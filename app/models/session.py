from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(settings.SQLALCHEMY_DATABASE_URI,
                       pool_pre_ping=True,
                       pool_size=30,
                       max_overflow=40
                    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
