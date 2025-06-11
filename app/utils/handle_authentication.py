import requests
from app.utils import enum


class AuthHandler:

    @staticmethod
    def get_oauth_token(client_id, client_secret, oauth_path):
        body = {
            "client_id": client_id,
            "client_secret": client_secret
        }
        auth_info = requests.post(oauth_path, json=body)
        return auth_info.json()

    @staticmethod
    def get_basic_auth(username, password):
        pass

    @staticmethod
    def authenticate(provider_obj):

        if provider_obj.auth_type == enum.AuthType.OAUTH.value:

            return AuthHandler.get_oauth_token(provider_obj.client_id,
                                               provider_obj.client_secret,
                                               provider_obj.oauth_path)

        if provider_obj.auth_type == enum.AuthType.BASIC.value:
            pass
