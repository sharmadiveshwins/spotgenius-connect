import unittest
import xml.etree.ElementTree as ET
from app.utils.common import DateTimeUtils
from app.utils.image_utils import ImageUtils
from app.utils.request_handler import RequestHandler
from app.utils.response_handler import ResponseHandler
from app.utils.schema_mapping import SchemaMapping
from app.utils.security import create_jwt_token
from app.models.base import Task, ConnectParkinglot


class TestIsFutureDate(unittest.TestCase):


    def test_past_date(self):
        past_date = "2010-01-01T00:00:00Z"
        self.assertFalse(DateTimeUtils.is_future_date(past_date))

    def test_empty_string(self):
        empty_date = ""
        self.assertFalse(DateTimeUtils.is_future_date(empty_date))

    def test_invalid_date_format(self):
        invalid_date = "not a date"
        self.assertFalse(DateTimeUtils.is_future_date(invalid_date))


def test_image_url_to_base64():
    assert ImageUtils.image_url_to_base64("https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png")


def test_map_value():
    task = Task(id=460, plate_number="ABC123", event_type='car.entry', created_at='2024-03-21 00:04:11.461',
                provider_type=1, parking_lot_id=1, feature_text_key="payment.check.lpr")
    updated_request_data = RequestHandler.map_value("{{plateNumber}}", {"requestDict": {"plateNumber": "ABC1"}}, task)
    assert updated_request_data


def test_make_post_request():
    response = RequestHandler.make_post_request("https://www.google.com", {"requestDict": {"plateNumber": "ABC1"}})
    assert response


def test_xml_to_dict():
    xml_string = """<ArrayOfValidParkingData><ValidParkingData>
        <Amount>0</Amount>
        <Article>
          <Id>9995</Id>
          <Name>SpotGenius</Name>
        </Article>
        <Code>NCTEST</Code>
        <ContainsTerminalOutOfCommunication/>
        <DateChangedUtc>2024-02-12T16:58:10</DateChangedUtc>
        <DateCreatedUtc>2024-02-12T16:58:10</DateCreatedUtc>
        <EndDateUtc>2024-02-12T17:15:02</EndDateUtc>
        <IsExpired>false</IsExpired>
        <ParkingSpace />
        <ParkingZone  />
        <PostPayment>
          <PostPaymentNetworkName/>
          <PostPaymentTransactionID  />
          <PostPaymentTransactionStatusKey  />
        </PostPayment>
        <PurchaseDateUtc>2024-02-12T16:58:02</PurchaseDateUtc>
        <StartDateUtc>2024-02-12T16:58:02</StartDateUtc>
        <Tariff>
          <Id>9995</Id>
          <Name>SpotGenius</Name>
        </Tariff>
        <Terminal>
          <Id>Spot-1</Id>
          <Latitude/>
          <Longitude/>
          <ParentNode>SpotGenius</ParentNode>
        </Terminal>
        <TicketNumber>0</TicketNumber>
        <Zone/>
      </ValidParkingData>
    </ArrayOfValidParkingData>"""
    xml_data = ET.fromstring(xml_string)
    assert ResponseHandler.xml_to_dict(xml_data)


def test_xml_to_json():
    assert ResponseHandler.xml_to_json("<xml></xml>")


def test_strip_namespace():
    assert ResponseHandler.strip_namespace("tag")


def test_map_value_to_citation_schema():
    task = Task(id=460, plate_number="ABC123", event_type='car.entry', created_at='2024-03-21 00:04:11.461',
                provider_type=1, parking_lot_id=1, feature_text_key="payment.check.lpr")
    assert SchemaMapping.map_value_to_citation_schema(task, {"provider_id": "provider_id", "plate_number": "plate_number"})


def test_create_jwt_token():
    assert create_jwt_token({}, "2024-02-22T08:02:00.488778")


def test_map_path_params():
    url = "{lpr}/{gracePeriod}"
    task = Task(id=460, plate_number="ABC123", event_type='car.entry', created_at='2024-03-21 00:04:11.461')
    connect_parkinglot = ConnectParkinglot(parking_lot_id=2, grace_period=1)
    assert RequestHandler.map_path_params(url, task, connect_parkinglot)


def test_map_key_values():
    original_dict = {"location_id": "location_id", "license_plate": "plate_number"}
    task = Task(id=460, plate_number="ABC123", event_type='car.entry', created_at='2024-03-21 00:04:11.461')
    assert RequestHandler.map_key_values(original_dict, task)
