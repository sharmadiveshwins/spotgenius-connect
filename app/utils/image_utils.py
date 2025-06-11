import os
import logging
import requests
import base64


logger = logging.getLogger(__name__)


class ImageUtils:

    @staticmethod
    def image_url_to_base64(url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            encoded_image = base64.b64encode(response.content)
            base64_string = encoded_image.decode('utf-8')
            return base64_string
        except Exception as e:
            logging.critical(f"Error: {str(e)}")
            return None

    @staticmethod
    def download_image_from_sg(token, image_url):
        headers = {
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        }
        response = None
        try:
            response = requests.post(
                os.getenv("SPOT_GENIUS_API_BASE_URL") + "/api/external/v1/download_image",
                json={"image_url": image_url},
                headers=headers,
            )
            response_data = response.json()
            if response.status_code == 200:
                response = response_data
            else:
                logger.error(f'Error on Image Utility: {response_data}')
        except Exception as e:
            logger.critical(f'Connection Error: {str(e)}')

        return response
