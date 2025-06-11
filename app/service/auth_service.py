import base64
import logging

from app import schema, config
from app.config import settings
from app.models import base
from app.models.provider_creds import ProviderCreds
from app.utils import enum
from app.utils.common import format_body
from app.utils.schema_mapping import SchemaMapping
from app.utils.security import create_jwt_token
from datetime import datetime, timedelta
from fastapi import HTTPException, Header, Depends
from starlette import status
import requests
from sqlalchemy.orm import Session
from app.dependencies.deps import get_db
from app.utils.security import decrypt_encrypted_value

json_db = {

    "amit": {
        "username": "amit",
        "password": "amit123",
    },

    "akash": {
        "username": "akash",
        "password": "akash123",
    }

}

logger = logging.getLogger(__name__)


class AuthService:

    @staticmethod
    def get_auth_info(provider_obj):
        body = {
            "client_id": provider_obj.client_id,
            "client_secret": provider_obj.client_secret
        }
        response = requests.post(provider_obj.oauth_path, json=body)
        return response

    @staticmethod
    def get_token(params: schema.PaymentProviderAuth.ParkMobileSchema):
        username = params.client_id
        password = params.client_secret
        user = json_db.get(username)
        if user and password == user.get("password"):
            create_access_key = {"sub": params.client_id}
            expire_time = datetime.utcnow() + timedelta(hours=1)
            return {
                "token": create_jwt_token(create_access_key, expire_time),
                "expire_time": expire_time,
                "status_code": status.HTTP_200_OK
            }

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

    @staticmethod
    def auth_impl(params: schema.PaymentProviderAuth.ParkMobileSchema):
        try:
            jwt_token = AuthService.get_token(params)
            if jwt_token["status_code"] == 200:
                save_token_schema = schema.SaveToken(access_token=jwt_token["token"],
                                                     expire_time=jwt_token["expire_time"])
                return save_token_schema
            else:
                raise HTTPException(status_code=jwt_token["status_code"])
        except Exception as e:
            logger.critical(f"Exception {str(e)}")
            raise e

    @staticmethod
    def verify_basic_auth(authorization: str = Header(...), db: Session = Depends(get_db)):

        try:
            encoded_auth = authorization.split(' ')[1]
            decoded_auth = base64.b64decode(encoded_auth).decode("utf-8")
            username, password = decoded_auth.split(':')

            logger.info(f"Authentication attempt for client_id: {username}")

            provider_creds_list = db.query(base.ProviderCreds).filter(
                base.ProviderCreds.client_id == username,
                base.ProviderCreds.text_key == enum.Provider.PROVIDER_PAYMENT_ARRIVE.value
            ).all()

            if not provider_creds_list:
                logger.warning(f"Authorization failed: No matching records for client_id '{username}'")
                raise HTTPException(status_code=401, detail="Unauthorized")

            for provider_creds in provider_creds_list:
                decrypted_secret = decrypt_encrypted_value(provider_creds.client_secret)

                if decrypted_secret == password:
                    logger.info(f"Password matched for client_id: {username}, proceeding with authentication")

                    if not provider_creds.access_token:
                        update_token = schema.SaveToken(access_token=encoded_auth)
                        provider_creds = ProviderCreds.update(db, provider_creds.id, update_token)
                        logger.info(f"Access token updated for client_id: {username}")

                    if authorization != f'Basic {provider_creds.access_token}':
                        logger.warning(f"Authorization failed: Token mismatch for client_id '{username}'")
                        raise HTTPException(status_code=401, detail="Unauthorized")

                    logger.info(f"Authorization successful for client_id: {username}")
                    return provider_creds.access_token

            logger.warning(f"Authorization failed: Password mismatch for client_id '{username}'")
            raise HTTPException(status_code=401, detail="Unauthorized")

        except HTTPException as http_error:
            raise HTTPException(status_code=http_error.status_code, detail=http_error.detail)

        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal Server Error")

    @staticmethod
    def verify_park_pliant(authorization: str = Header(None)):
        if authorization != f'Basic {config.settings.CALLBACKS_AUTHORIZATION_TOKEN}':
            raise HTTPException(status_code=401, detail="Unauthorized")

    @staticmethod
    def generate_basic_auth_token(username, password):
        user_pass = f"{username}:{password}"
        user_pass_bytes = user_pass.encode('ascii')

        base64_bytes = base64.b64encode(user_pass_bytes)
        basic_auth_token = base64_bytes.decode('ascii')

        return basic_auth_token

    @staticmethod
    def verify_api_key_data_ticket(api_key: str = Header(..., alias="API-KEY")):

        print("api_key: ", api_key)
        print("env data ticket: ", settings.DATA_TICKET_API_KEY)
        if api_key != settings.DATA_TICKET_API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API Key")
        return True

    @staticmethod
    def login(db, models_dict, mapped_data):

        url = models_dict['provider'].api_endpoint + models_dict['provider'].oauth_path
        mapped_body = SchemaMapping.replace_json_placeholder_with_mapped_pointers(models_dict['provider'].meta_data['request']['body'], models_dict)
        formatted_body = format_body(mapped_body)
        logger.debug(f'Requesting URL {url} with body {formatted_body}')

        try:
            response = requests.post(url, json=formatted_body)  # Use `json=pointers` for a JSON body
            response.raise_for_status()  # Raises HTTPError for bad responses

            logger.debug(f'Response from URL {url}: {response.text}')

            response_data = response.json()  # Ensure JSON parsing of response
            logger.debug(f'Token found {response_data.get("Token", "0")}')

            token = response_data.get('Token')
            if token:
                models_dict['provider_creds'].update_token(db, models_dict['provider_creds'].id, token)
                mapped_data['Token'] = token
                return mapped_data
            else:
                logger.error(f"No Token found in response from {url}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error during OAuth request to {url}: {str(e)}")

    @staticmethod
    def generate_bearer_token(db, models_dict):

        url = models_dict['provider'].api_endpoint + models_dict['provider'].oauth_path
        mapped_body = SchemaMapping.replace_json_placeholder_with_mapped_pointers(
            models_dict['provider'].meta_data['request']['body'], models_dict)

        logger.debug(f'Requesting URL {url} with body {mapped_body}')

        try:
            response = requests.post(url, data=mapped_body)
            response.raise_for_status()
            logger.debug(f'Response from URL {url}: {response.text}')
            response_data = response.json()

            logger.debug(f'Token found {response_data.get("Token", "0")}')
            token = response_data.get('access_token')

            if token:
                models_dict['provider_creds'].update_token(db, models_dict['provider_creds'].id, token)
                return token
            else:
                logger.error(f"No Token found in response from {url}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error during OAuth request to {url}: {str(e)}")


    @staticmethod
    def verify_authorization_oobeo(authorization: str = Header(...), db: Session = Depends(get_db)):
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid Authorization header")

        token = authorization.split(" ")[1]
        provider_creds = db.query(base.ProviderCreds).filter(base.ProviderCreds.text_key == "provider.enforcement.oobeo").first()
        # Decode and validate the token
        try:
            decoded = base64.b64decode(token).decode()
            if decoded != f"{provider_creds.client_id}:{decrypt_encrypted_value(provider_creds.client_secret)}":
                raise HTTPException(status_code=401, detail="Invalid credentials")
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token format")

    @staticmethod
    def generate_basic_base_64(db, models_dict):

        provider_creds = models_dict['provider_creds']
        combine_creds = f'{provider_creds.client_id}:{decrypt_encrypted_value(provider_creds.client_secret)}'
        encoded_bytes = base64.b64encode(combine_creds.encode('utf-8'))
        encoded_str = f"Bearer {encoded_bytes.decode('utf-8')}"
        if encoded_str:
            models_dict['provider_creds'].update_token(db, models_dict['provider_creds'].id, encoded_str)
        return encoded_str

    @staticmethod
    def can_access_provider(request) -> bool:

        email = request.headers.get("email", "").strip().lower()
        role = request.headers.get("role", "").strip().lower()

        return role in enum.AccessControl.CAN_VIEW.value or email.split("@")[-1] in enum.AccessControl.CAN_VIEW.value




