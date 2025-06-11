import requests
import logging
from app.config import settings
from app.models.users import User

logger = logging.getLogger(__name__)


class SGAdminApis:

    # def __init__(self, url, request):
    #
    #     self.url = url
    #     self.request = request

    def __enter__(self):
        return self

    def vehicle_privilege_permit(self, db, parking_lot_id, lpr):
        try:
            privilege_permit_response = None
            sg_connect_admin_client = User.get_by_user_name(db, 'sg-connect-admin-api-client')

            if sg_connect_admin_client:
                response = self.__call_vehicle_privilege_permit(sg_connect_admin_client.token, parking_lot_id, lpr)

                if response.status_code == 200:
                    privilege_permit_response = response.json()
                elif response.status_code == 401:
                    token = self.__authenticate(db, sg_connect_admin_client)
                    response = self.__call_vehicle_privilege_permit(token, parking_lot_id, lpr)

                    if response.status_code == 200:
                        privilege_permit_response = response.json()

            logger.info(f"Privilege Permit response - LPR: {lpr} - {privilege_permit_response}")

            return privilege_permit_response

        except Exception as e:
            logger.error(str(e))
            return None


    def lpr_exit_status(self, db, parking_lot_id, lpr_record_id):
        try:
            lpr_exit_status_response = None
            sg_connect_admin_client = User.get_by_user_name(db, 'sg-connect-admin-api-client')

            if sg_connect_admin_client:
                response = self.__get_lpr_exit_status(sg_connect_admin_client.token, parking_lot_id, lpr_record_id)

                if response.status_code == 200:
                    lpr_exit_status_response = response.json()
                elif response.status_code == 401:
                    token = self.__authenticate(db, sg_connect_admin_client)
                    response = self.__get_lpr_exit_status(token, parking_lot_id, lpr_record_id)

                    if response.status_code == 200:
                        lpr_exit_status_response = response.json()

            logger.info(f"LPR status response - LPR: {lpr_record_id} - {lpr_exit_status_response}")

            return lpr_exit_status_response

        except Exception as e:
            logger.error(str(e))
            return None


    def spot_status(self, db, parking_lot_id, spot_name):
        try:
            spot_status_response = None
            sg_connect_admin_client = User.get_by_user_name(db, 'sg-connect-admin-api-client')

            if sg_connect_admin_client:
                response = self.__get_spot_status(sg_connect_admin_client.token, parking_lot_id, spot_name)

                if response.status_code == 200:
                    spot_status_response = response.json()
                elif response.status_code == 401:
                    token = self.__authenticate(db, sg_connect_admin_client)
                    response = self.__get_spot_status(token, parking_lot_id, spot_name)

                    if response.status_code == 200:
                        spot_status_response = response.json()

            if spot_status_response:
                logger.info(
                    f"Spot status response - Spot: {spot_name} - spot status: {spot_status_response.get('spot_status')} -"
                )
            else:
                logger.info(
                    f"Spot status response - Spot: {spot_name} - spot status response {spot_status_response} -"
                )

            return spot_status_response

        except Exception as e:
            logger.error(str(e))
            return None


    def lot_status(self, db, parking_lot_id):
        try:
            lot_status_response = None
            sg_connect_admin_client = User.get_by_user_name(db, 'sg-connect-admin-api-client')

            if sg_connect_admin_client:
                response = self.__get_lot_status(sg_connect_admin_client.token, parking_lot_id)

                if response.status_code == 200:
                    lot_status_response = response.json()
                elif response.status_code == 401:
                    token = self.__authenticate(db, sg_connect_admin_client)
                    response = self.__get_lot_status(token, parking_lot_id)

                    if response.status_code == 200:
                        lot_status_response = response.json()

            logger.info(f"Lot status response - lot: {parking_lot_id} - {lot_status_response}")

            return lot_status_response

        except Exception as e:
            logger.error(str(e))
            return None


    def __get_lot_status(self, token, parking_lot_id):
        headers = {
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        }

        response = requests.get(
            f"{settings.SPOT_GENIUS_API_BASE_URL}/api/external/v1/parking_lot/{parking_lot_id}/lot_status",
            headers=headers,
            timeout=settings.SG_ADMIN_API_REQUEST_TIMEOUT
        )

        return response


    def __call_vehicle_privilege_permit(self, token, parking_lot_id, lpr):
        headers = {
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        }

        response = requests.get(
            f"{settings.SPOT_GENIUS_API_BASE_URL}/api/external/v1/parking_lot/{parking_lot_id}/check_permit/{lpr}",
            headers=headers,
            timeout=settings.SG_ADMIN_API_REQUEST_TIMEOUT
        )

        return response


    def __get_lpr_exit_status(self, token, parking_lot_id, lpr_record_id):
        headers = {
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        }

        response = requests.get(
            f"{settings.SPOT_GENIUS_API_BASE_URL}/api/external/v1/parking_lot/{parking_lot_id}/check_lpr_exit/{lpr_record_id}",
            headers=headers,
            timeout=settings.SG_ADMIN_API_REQUEST_TIMEOUT
        )

        return response


    def __get_spot_status(self, token, parking_lot_id, spot_name):
        headers = {
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        }

        response = requests.get(
            f"{settings.SPOT_GENIUS_API_BASE_URL}/api/external/v1/parking_lot/{parking_lot_id}/{spot_name}/spot_status",
            headers=headers,
            timeout=settings.SG_ADMIN_API_REQUEST_TIMEOUT
        )

        return response


    def __authenticate(self, db, sg_connect_admin_client):
        form_data = {
            "client_id": sg_connect_admin_client.client_id,
            "client_secret": sg_connect_admin_client.client_secret
        }

        response = requests.post(
            f"{settings.SPOT_GENIUS_API_BASE_URL}/api/oauth/token",
            data=form_data,
            timeout=settings.SG_ADMIN_API_REQUEST_TIMEOUT
        )

        if response.status_code == 200:
            token = response.text
            token = token.replace('"', '')

            sg_connect_admin_client.token = token
            db.commit()

            return token

        return None


    def __exit__(self, exc_type, exc_value, traceback):
        pass
