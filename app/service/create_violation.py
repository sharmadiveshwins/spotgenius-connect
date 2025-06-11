import os
import requests
from app import schema


class CreateViolation:

    @staticmethod
    def set_alert_schema(parking_lot_id,
                         parking_spot_id,
                         category,
                         severity,
                         alert_type,
                         alert_type_id,
                         alert_action,
                         alert_state,
                         alert_trigger_state,
                         title,
                         details,
                         image_base64s
                         ):
        return schema.CreateAlert(
            parking_lot_id=parking_lot_id,
            parking_spot_id=parking_spot_id,
            category=category,
            severity=severity,
            alert_type=alert_type,
            alert_type_id=alert_type_id,
            alert_action=alert_action,
            alert_state=alert_state,
            alert_trigger_state=alert_trigger_state,
            title=title,
            details=details,
            image_base64s=image_base64s
        )

    @staticmethod
    def send_alert(alert_details, token: str):
        """
        Create an alert on SpotGenius by first integrating with a third-party API and carrying out the desired process.
        """
        headers = {
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        }

        response = requests.post(
            os.getenv("SPOT_GENIUS_API_BASE_URL") + "/api/ai_integrations/create_alert",
            json=schema.CreateAlert(**alert_details.dict()).model_dump(),
            headers=headers,
        )
        return response
