from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings


def get_db_session():
    # Create a SQLAlchemy engine
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    db_session = Session()
    return db_session
