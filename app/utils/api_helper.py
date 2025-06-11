import requests
import logging

from typing import Optional, Any, Dict
from fastapi import status, HTTPException

from app.config import settings

logger = logging.getLogger(__name__)


class ApiHelper:
    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, Any]] = None,
        timeout: int = settings.DEFAULT_EXTERNAL_API_REQUEST_TIMEOUT_SEC,
    ):
        base_headers = {"Content-Type": "application/json"}

        self.base_url = base_url.rstrip("/")
        self.headers = {**(headers or {}), **base_headers}
        self.timeout = timeout

    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:

        url = f"{self.base_url}/{endpoint}"
        request_headers = {**self.headers, **(headers or {})}

        try:
            logger.info(
                f"initiating api request method:{method}, url {url}, data:{data}, json:{json}"
            )
            response = requests.request(
                method=method.upper(),
                url=url,
                params=params,
                data=data,
                json=json,
                headers=request_headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.info(f"got response from url: {url}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(
                f"error while making api request: {url}, error: {e}, data:{data}, json:{json}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error while making api request",
            )

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        return self.request("GET", endpoint, params=params, headers=headers)

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        return self.request("POST", endpoint, data=data, json=json, headers=headers)

    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        return self.request("PUT", endpoint, data=data, json=json, headers=headers)

    def delete(self, endpoint: str, headers: Optional[Dict[str, str]] = None):
        return self.request("DELETE", endpoint, headers=headers)
