import logging

from fastapi import HTTPException, Header, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from starlette import status

from app.config import settings
from datetime import datetime
from hashlib import sha256
from passlib.context import CryptContext

from app.dependencies.deps import get_db
from app.schema import Session
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

secret_key = settings.FERNET_ENCRYPTION_KEY
fernet = Fernet(secret_key)


def create_jwt_token(data: dict, expire_time: datetime):
    data['exp'] = expire_time
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_jwt_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception as e:
        logger.critical(f"Exception {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid credentials")


def verify_token(authorization: str = Header(...),
                 organization: int = Header(...),
                 db: Session = Depends(get_db)):
    try:
        token = authorization.split(' ')[1]
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        client_id: str = payload.get("client_id")
        token_org_id: int = payload.get("org_id")

        if client_id is None or token_org_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        if organization != token_org_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Organization ID does not match token payload")
        # Authenticate the user
        from app.models import base
        user = base.User.get_by_client_id(db, client_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        client_secret = user.client_secret
        client = base.User.authenticate_user(client_id, client_secret, db)

        if client is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        return {'status': 'success', 'message': 'Token is valid'}

    except JWTError as e:
        logger.error(f"Token decode error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"An error occurred during token verification: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


def get_hashed_oauth_client_secret(client_secret: str) -> str:
    return sha256(client_secret.encode("utf-8")).hexdigest()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password):
    return pwd_context.hash(password)


def encrypt_value(value: str) -> str:
    encoded_value = value.encode()
    encrypted_value = fernet.encrypt(encoded_value)
    return encrypted_value.decode()


def decrypt_encrypted_value(encrypted_value: str) -> str:
    try:
        decrypted_value = fernet.decrypt(encrypted_value)
        value = decrypted_value.decode("utf-8")
        return value
    except:
        return encrypted_value


def is_encrypted(value):
    # Check if the value starts with 'ENC:', indicating it is encrypted
    if isinstance(value, str) and value.startswith("ENC:"):
        return True
    if isinstance(value, str) and value.startswith("gAAAAA"):
        return True
    return False
