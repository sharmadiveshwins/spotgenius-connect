import json
import logging
from sqlalchemy.orm import Session
from app.models import base
from app.wrapper.process_request import ProcessRequest
from app.utils.response_handler import ResponseHandler


logger = logging.getLogger(__name__)

class Notifier:

    @staticmethod
    def inactivate_violation_in_provider_dashboard(db: Session, task, sub_tasks):

        connect_parkinglot = base.ConnectParkinglot.get_connect_parking_lot_id(db, task.parking_lot_id)
        for sub_task in sub_tasks:
            feature_by_id = base.FeatureUrlPath.get_feature_url_path_by_id(db, sub_task.feature_url_path)
            provider_creds_by_id = base.ProviderCreds.get_by_id(db, sub_task.provider_creds_id)
            violations = base.Violation.get_all_violation_associate_with_session(db, task.session_id)
            if violations:
                for violation in violations:
                    logger.info(f'Violation inactivation process started for session {task.session_id} and violation type: '
                                f'{violation.name}')
                    data = ProcessRequest.process(db=db,
                                                  task=task,
                                                  sub_task=sub_task,
                                                  feature=feature_by_id,
                                                  provider_creds=provider_creds_by_id,
                                                  connect_parkinglot=connect_parkinglot,
                                                  violation=violation
                                                  )

                    provider_name = base.Provider.get_provider_by_id(db, provider_creds_by_id.provider_id).name
                    logger.info(f'Received response {data} from provider {provider_name}')
                    json_response_schema = json.loads(feature_by_id.response_schema)
                    if data is not None:
                        results = ResponseHandler.replace_json_values(data, json_response_schema)
                        if results['status']:
                            attribute_to_update = {"citation_inactivation_id": results.get('response_id')}
                            base.Violation.update_by_violation_and_session_id(db, task.session_id, violation.id,
                                                                                  attribute_to_update)

                            logger.info(
                                f'Violation inactivation completed for session {task.session_id}, Violation type: {violation.name}'
                                f' inactivation id mapped with Violation')

        base.SubTask.close_sub_task(db, sub_task.id)
