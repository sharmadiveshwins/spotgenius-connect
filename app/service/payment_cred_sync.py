import logging
from typing import Any, Optional, Dict, List
from app.config import settings
from app.utils.api_helper import ApiHelper
from starlette.responses import JSONResponse
from app.utils.retry_helper import retry_async_on_failure


logger = logging.getLogger(__name__)


class PaymentService(ApiHelper):
    def __init__(self):
        super().__init__(
            settings.PAYMENT_SERVICE_BASE_URL,
            {},
            settings.DEFAULT_EXTERNAL_API_REQUEST_TIMEOUT_SEC,
        )

    @retry_async_on_failure(max_retries=3, sleep_times=[1, 2, 4])
    def create_provider_instances_bulk(self, payload_list: List[Dict[str, Any]]):
        if not payload_list:
            logger.warning("[PaymentService] No payload provided for bulk provider creation.")
            return []

        endpoint = "api/v1/connect/providers/instances"

        try:
            response = self.post(endpoint=endpoint, json=payload_list)

            status_code = response.get("status_code")

            if 200 <= status_code < 300:
                if "data" in response:
                    return response["data"]
                else:
                    logger.warning(f"[PaymentService] Unexpected response format: {response}")
                    return [{"status": "error", "message": "Unexpected response from PaymentService"}]

            if status_code == 500:
                return [{"status": "error", "message": response.get("message", "Unknown error")}]

            logger.error(f"[PaymentService] Bulk creation failed with status code {status_code}")
            return [{"status": "error", "message": "Unexpected error from PaymentService"}]

        except Exception as e:
            logger.error(f"[PaymentService] Bulk creation failed: {str(e)}")
            return [{"status": "error", "message": str(e)}]
    
    @retry_async_on_failure(max_retries=3, sleep_times=[1, 2, 4])
    def send_cred_update_payload(self, payload: Dict[str, Any]):
        """Send the bulk payload to handle updates and detachments."""
        try:
            response = self.put(
                endpoint="api/v1/connect/providers/instance/bulk-update",
                json=payload,
            )

            logger.info(f"[PaymentService] - Received response: {response}")

            status_code = response.get("status_code")
            if 200 <= status_code < 300:
                logger.info("PaymentService - Bulk update successful.")
                return response
            else:
                logger.error(f"[PaymentService] - Bulk update failed with status code {status_code}")
                return {"status": "error", "message": response.get("message", "Unknown error")}

        except Exception as e:
            logger.error(f"[PaymentService] - Error during bulk update: {str(e)}")
            return {"status": "error", "message": f"Error during bulk update: {str(e)}"}

payment_service = PaymentService()
