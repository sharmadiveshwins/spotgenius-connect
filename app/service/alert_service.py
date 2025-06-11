import logging
import os
import requests

from app.schema import session_schema
from app.schema.alert_schema import AlertCreateSchema
from app.service import session_manager
from app.utils.image_utils import ImageUtils
from app.config import settings
from app.utils import enum
from app.utils.common import car_identification_log

logger = logging.getLogger(__name__)


class AlertSgadmin:
    """
    Alert Service itegration with spotgenius admin.
    """

    @staticmethod
    def create_alert(create_alert_schema):
        headers = {
            "Authorization": "Bearer {}".format(settings.TOKEN_FOR_CREATE_ALERT_API),
            "Content-Type": "application/json",
        }
        response = None
        try:
            response = requests.post(
                os.getenv("SPOT_GENIUS_API_BASE_URL") + "/api/external/v1/create_alert",
                json=create_alert_schema.model_dump(),
                headers=headers,
            )
            response_data = response.json()
            if response.status_code == 200 or response.status_code == 201:
                response = response_data
            else:
                logger.error(f'Error on Alert Service: {response_data}')
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
    def update_alert(alert_update_schema):
        logger.debug(f"calling update alert api with request body {alert_update_schema.model_dump()}")
        headers = {
            "Authorization": "Bearer {}".format(settings.TOKEN_FOR_CREATE_ALERT_API),
            "Content-Type": "application/json",
        }
        response = None

        try:
            response = requests.put(
                os.getenv("SPOT_GENIUS_API_BASE_URL") + f"/api/external/v1/update_alert",
                json=alert_update_schema.model_dump(),
                headers=headers,
                timeout=settings.REQUEST_TIMEOUT
            )
            logger.debug(f"Response from update alert api {response}")
        except Exception as e:
            logger.critical(f'Exception: {str(e)}')

        return response

    @staticmethod
    def process_alert(db, task, violation):
        images_urls = [task.sg_event_response.get('frame_image_url'),
                       task.sg_event_response.get('vehicle_crop_image_url'),
                       task.sg_event_response.get('lpr_crop_image_url')]

        # car_identification for dynamically showing logs for LPR or Spot based
        car_identification = car_identification_log(task)

        image_base64s = [ImageUtils.image_url_to_base64(image_url) for image_url in images_urls if image_url]
        alert_type_id = 39  # alert type id taken from sg-admin (thirdpartytest.spotgenius) for payment violation
        alert_description = f"Payment violation has been detected for the vehicle with the plate number" \
                            f" {task.plate_number}."

        if task.feature_text_key == enum.Feature.PAYMENT_CHECK_SPOT.value:
            alert_description = f"Payment violation has been detected for the vehicle with the Spot Id" \
                                f" {task.parking_spot_id}."

        create_alert_schema = AlertCreateSchema(title='Payment Violation',
                                                severity='high',
                                                category='violation',
                                                subcategory="Non Payment",
                                                alert_type='info',
                                                alert_type_id=alert_type_id,
                                                parking_lot_id=task.parking_lot_id,
                                                image_base64s=image_base64s,
                                                details=alert_description,
                                                license_plate_number=task.plate_number,
                                                alert_state='open',
                                                parking_spot_id=task.parking_spot_id,
                                                alert_trigger_state='active')

        sg_admin_alert = AlertSgadmin.create_alert(create_alert_schema)

        sg_admin_alert_list = []
        if sg_admin_alert:
            attributes_to_update = {"is_waiting_for_payment": False}
            session_manager.SessionManager.create_session_logs(db,
                                                               session_id=task.session_id,
                                                               action_type="Alert Sent",
                                                               attributes_dict=attributes_to_update,
                                                               description="Alert Sent")

            logger.warning(
                f"Task: {task.id} / {car_identification} - Violation found and created with Id: {violation.id} / Alert: {sg_admin_alert.get('id')} ")
            if task.sgadmin_alerts_ids:
                task.sgadmin_alerts_ids.append(sg_admin_alert['id'])
                sg_admin_alert_list = task.sgadmin_alerts_ids
            else:
                sg_admin_alert_list.append(sg_admin_alert['id'])
                task.sgadmin_alerts_ids = sg_admin_alert_list
                db.commit()
                db.refresh(task)

        return sg_admin_alert_list
