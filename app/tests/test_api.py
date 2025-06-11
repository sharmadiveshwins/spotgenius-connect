import unittest
from unittest.mock import MagicMock
from app.api.subscribe_api import *


class TestSubscribeApi(unittest.TestCase):
    def test_subscribe_sg(self):
        test_data = {
            "parking_lot_id": 2,
            "parking_lot_name": "449 S Spring Street",
            "event_key": "lpr_entry",
            "license_plate": "ABC1",
            "entry_time": "2024-02-22T08:02:00.488778",
            "make": "suv",
            "model": "Honda Odyssey",
            "color": "black",
            "timestamp": "2024-02-22T08:02:00.488778",
            "vehicle_orientation": "forward",
            "region_code": None,
            "region_name": None,
            "frame_image_url": "https://prodpublicartifacts.blob.core.windows.net/public-artifact-images/lpr_images/123/529/detection_images/61ad1568-5023-4b30-89f6-eb96dd13e608",
            "vehicle_crop_image_url": "https://prodpublicartifacts.blob.core.windows.net/public-artifact-images/lpr_images/123/529/vehicle_images/f378281c-8acb-4883-94ef-0d078ffe4d97",
            "lpr_crop_image_url": "https://prodpublicartifacts.blob.core.windows.net/public-artifact-images/lpr_images/123/529/plate_images/52b7f398-1d97-4048-95cb-9b32b5ce6c9e",
            "lpr_record_id": 1
        }
        response = subscribe_sg(test_data)
        self.assertEqual(response.status_code, 200)


class TestSubscribeArrive(unittest.TestCase):

    def test_all_fields_provided(self):
        data = {
            "event": {
                "type": "create"
            },
            "resource": {
                "resource_type": "booking",
                "location_id": 54861,
                "location_name": "Generic Push Integration Testing",
                "license_plate": "inout8",
                "start_date_time": "2024-06-28T12:52:56",
                "end_date_time": "2024-06-29T09:30:56",
                "price_paid": {
                    "USD": "20.00"
                },
                "full_price": {
                    "USD": "0.00"
                },
                "seller_gross_price": {
                    "USD": "0.00"
                },
                "venue_id": None,
                "amenities": [
                    {
                        "name": "indoor",
                        "enabled": False
                    },
                    {
                        "name": "security",
                        "enabled": False
                    },
                    {
                        "name": "valet",
                        "enabled": False
                    },
                    {
                        "name": "restroom",
                        "enabled": False
                    },
                    {
                        "name": "unobstructed",
                        "enabled": True
                    },
                    {
                        "name": "tailgate",
                        "enabled": False
                    },
                    {
                        "name": "handicap",
                        "enabled": False
                    },
                    {
                        "name": "vehicle_charging",
                        "enabled": False
                    },
                    {
                        "name": "reentry_allowed",
                        "enabled": False
                    },
                    {
                        "name": "eticket",
                        "enabled": False
                    },
                    {
                        "name": "rv",
                        "enabled": False
                    },
                    {
                        "name": "attended",
                        "enabled": False
                    }
                ]
            }
        }
        db_mock = MagicMock()
        auth_token_mock = 'fake_auth_token'

        response = subscribe_arrive(data, db=db_mock, auth_token=auth_token_mock)

        self.assertEqual(response.status_code, 204)

    def test_incorrect_field_type(self):
        data = {
            'resource': {
                'start_date_time': '2022-01-01T00:00:00',
                'end_date_time': '2022-01-01T01:00:00',
                'price_paid': {'USD': '100'},  # Incorrect type: string instead of int
                'license_plate': 'ABC123',
                'resource_id': '12345',
                'location_id': '67890'
            }
        }
        db_mock = MagicMock()
        auth_token_mock = 'fake_auth_token'

        response = subscribe_arrive(data, db=db_mock, auth_token=auth_token_mock)

        self.assertEqual(response.status_code, 204)
        db_mock.query.assert_called_once_with(base.ProviderCreds)
        db_mock.create.assert_not_called()
