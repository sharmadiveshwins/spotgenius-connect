import logging
import os
import requests
from app.schema import CreateAlert, UpdateAlert

logger = logging.getLogger(__name__)


class AlertSgadmin:
    """
    Create an alert on SpotGenius by first integrating with a third-party API and carrying out the desired process.
    """

    @staticmethod
    def create_alert(alert_details, token: str):
        headers = {
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        }
        response = None
        try:
            response = requests.post(
                os.getenv("SPOT_GENIUS_API_BASE_URL") + "/api/external/v1/create_alert",
                json=CreateAlert(**alert_details.dict()).model_dump(),
                headers=headers,
            )
            response_data = response.json()
            if response.status_code == 200 or response.status_code == 201:
                response = response_data
            else:
                logger.error(f'Error on Create Alert: {response_data}')
        except Exception as e:
            logger.critical(f'Exception: {str(e)}')

        return response

    @staticmethod
    def get_alert_details(alert_id, token: str):
        headers = {
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        }

        response = requests.get(
            os.getenv("SPOT_GENIUS_API_BASE_URL") + f"/api/external/v1/get_alert/{alert_id}",
            headers=headers,
        )
        return response

    @staticmethod
    def update_alert(alert_details, token: str):
        headers = {
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        }

        response = requests.put(
            os.getenv("SPOT_GENIUS_API_BASE_URL") + f"/api/external/v1/update_alert",
            json=UpdateAlert(**alert_details.dict()).model_dump(),
            headers=headers,
        )
        return response
