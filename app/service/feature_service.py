import logging
from app.utils import enum
from app.service.features.check_payment_by_lpr import CheckPaymentByLPR
from app.service.features.check_reservation_by_lpr import CheckReservationByLPR
from app.service.features.check_payment_by_spot import CheckPaymentBySpot
from app.service.features.check_payment import get_payment_status
from app.service.features.make_payment_by_lpr import MakePaymentByLPR
from app.service.features.citation import Citation
from app.service.features.notify_sg_admin import NotifySgAdmin
from app.service.features.inactivation_notifier import Notifier
from app.service.features.check_payment_by_spot import CheckPaymentBySpot
from app.utils.enum import Feature

logger = logging.getLogger(__name__)


class FeatureService:

    @staticmethod
    def switch_feature(db, task, sub_task):

        if task.feature_text_key == enum.Feature.PAYMENT_CHECK_LPR.value:
            CheckPaymentByLPR.check_payment_by_lpr(db, task, sub_task)

        elif task.feature_text_key == enum.Feature.PAYMENT_CHECK_SPOT.value:
            CheckPaymentBySpot.check_payment_by_spot(db, task, sub_task)
        
        if task.feature_text_key == enum.Feature.RESERVATION_CHECK_LPR.value:
            CheckReservationByLPR.check_reservation_by_lpr(db, task, sub_task)

        elif task.feature_text_key == enum.Feature.RESERVATION_CHECK_SPOT.value:
            return 'This will be implemented later'

        elif task.feature_text_key == enum.Feature.PAYMENT_MAKE_LPR.value:
            MakePaymentByLPR.make_payment_by_lpr(db, task, sub_task)

        elif task.feature_text_key == enum.Feature.ENFORCEMENT_CITATION.value:
            logger.info(f'processing {enum.Feature.ENFORCEMENT_CITATION.value} task with id {task.id}')
            Citation.create_citation(db, task, sub_task)

        elif task.feature_text_key == enum.Feature.NOTIFY_SG_ADMIN.value:
            NotifySgAdmin.send_alerts(db, task, sub_task)

        elif task.feature_text_key == enum.Feature.ENFORCEMENT_NOTIFICATION.value:
            logger.info(f"Processing task for back Notification to update violation as inactivate")
            Notifier.inactivate_violation_in_provider_dashboard(db, task, sub_task)

        else:
            logger.debug(f"{task.feature_text_key} feature not available.")
