import logging

from app.models.session import SessionLocal
from typing import Optional, Generator
from fastapi import Query

logger = logging.getLogger(__name__)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.critical(f"Exception {str(e)}")
    finally:
        db.close()


def get_org_id(org_id: int = Query(...)):
    return org_id
