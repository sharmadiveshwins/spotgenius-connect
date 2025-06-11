from app.utils.enum import EventsForSessionLog
from app.utils.sg_admin_apis import SGAdminApis
from app.service import session_manager
from app.models.session_log import SessionLog


class PrivilegePermit:

    @staticmethod
    def check_privilege_permit(db, connect_parkinglot, task):        
        # To avoid two times privilege permit in session log, when lot is configured with both reservation and payment
        privilege_permit_exists_in_session_log = SessionLog.check_last_session_by_action_type(db, task.session_id, [
                EventsForSessionLog.PRIVILEGE_PERMIT.value])

        if privilege_permit_exists_in_session_log:
            return {
                "is_privilege_permit": True,
                "expiry_at": None, 
                "message": "Privilege permit already exists in session log."
            }

        privilege_permit = SGAdminApis().vehicle_privilege_permit(db, connect_parkinglot.parking_lot_id, task.plate_number)

        if privilege_permit and privilege_permit['is_privilege_permit']:
            session_manager.SessionManager.create_session_logs(
                db,
                session_id=task.session_id,
                action_type=EventsForSessionLog.PRIVILEGE_PERMIT.value,
                description=EventsForSessionLog.PRIVILEGE_PERMIT.value
            )

            return privilege_permit

        return False
