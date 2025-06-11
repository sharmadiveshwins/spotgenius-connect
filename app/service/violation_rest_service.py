import logging

from typing import Any, Optional, Dict, List

from app.config import settings
from app.utils.api_helper import ApiHelper
from app.utils.retry_helper import retry_async_on_failure

logger = logging.getLogger(__name__)


class ViolationService(ApiHelper):
    def __init__(self):
        super().__init__(
            settings.VIOLATION_SERVICE_BASE_URL,
            {},
            settings.DEFAULT_EXTERNAL_API_REQUEST_TIMEOUT_SEC,
        )

    @retry_async_on_failure(max_retries=3, sleep_times=[1, 2, 4])
    def bulk_upsert_violation_configs(
        self,
        configurations: List[Dict]
    ):
        if not settings.IS_VIOLATION_SERVICE_ENABLED:
            return

        payload = {
            "configurations": configurations
        }

        response = self.post(
            endpoint=f"api/v1/lots/violation_configurations/bulk",
            json=payload,
        )

        logger.info(
            f"Bulk upsert {len(configurations)} violation configurations"
        )
        return response

    @retry_async_on_failure(max_retries=3, sleep_times=[1, 2, 4])
    def update_violation_config(
            self,
            parking_lot_id: int,
            org_id: int,
            scope: str,
            scope_id: int,
            configuration: Dict[str, Any],
            modified_by: Optional[str] = "",
    ):
        if not settings.IS_VIOLATION_SERVICE_ENABLED:
            return

        response = self.put(
            endpoint=f"api/v1/lots/{parking_lot_id}/violation_configurations",
            json={
                "parking_lot_id": parking_lot_id,
                "org_id": org_id,
                "scope": scope,
                "scope_id": scope_id,
                "configuration": configuration,
                "modified_by": modified_by,
            },
        )
        violation_config_data = response.get("data") or {}
        logger.info(
            f"created violation service with id: {violation_config_data.get('id')}"
        )

violation_service = ViolationService()
