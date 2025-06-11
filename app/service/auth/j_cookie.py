import logging
from app.utils.schema_mapping import SchemaMapping
from app.utils.request_handler import RequestHandler
from app.utils.security import encrypt_value
import requests

logger = logging.getLogger(__name__)


class JCookie:

    @staticmethod
    def auth(db, provider, provider_connect, provider_creds):
        model_data = {
            "provider": provider,
            "provider_connect": provider_connect,
            "provider_cred": provider_creds
        }

        request_output_schema = SchemaMapping.replace_json_placeholder_with_mapped_pointers(provider.meta_data,
                                                                                            model_data)
        request_data = RequestHandler.make_request_data(request_output_schema)
        response = requests.request(method=request_data['method'], url=request_data['url'], data=request_data['body'],
                                    headers=request_data['headers'])

        if response.status_code == 200:
            if response.cookies:
                for cookie in response.cookies:
                    cookie = f"{cookie.name}={cookie.value}"

                # save cookies for specific parking lot provider's cred
                provider_creds.access_token = encrypt_value(cookie)
                db.add(provider_creds)
                db.commit()
                db.refresh(provider_creds)
