from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from app.dependencies.deps import get_db
from datetime import datetime
from app.models.simulation import Simulation
from app.schema.simulation_schema import SimulationCreateSchema
from app.service import AuthService
from app.utils.simulation import SimulationUtils

simulation_router = APIRouter()


# API to insert JSON data
@simulation_router.post("/records/{provider_id}/{api_type}")
def create(simulation_data: SimulationCreateSchema, provider_id, api_type, db: Session = Depends(get_db)):
    try:
        for list_item in simulation_data.input_data:
            db_item = Simulation(
                input_data=list_item,
                provider_id=provider_id,
                api_type=api_type
            )

            db.add(db_item)

        db.commit()
        return {"message": "Items inserted successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@simulation_router.get("/tiba/reservations")
def get_reservations(provider_id: int,
                     ValidFrom: datetime = Depends(SimulationUtils.parse_valid_from),
                     ValidTo: datetime = Depends(SimulationUtils.parse_valid_to),
                     db: Session = Depends(get_db)):
    output = Simulation.filterTibaRecords(db, 'ValidFrom', 'ValidTo', ValidFrom, ValidTo, provider_id, 'reservation')

    return {
        "ListItems": output
    }


@simulation_router.get("/tiba/monthly_pass")
def get_monthly_pass(provider_id: int,
                     db: Session = Depends(get_db)):
    month_range = SimulationUtils.month_date_range()
    ValidFrom = month_range['start_date']
    ValidTo = month_range['end_date']

    output = Simulation.filterTibaRecords(db, 'ValidFromStr', 'ValidToStr', ValidFrom, ValidTo, provider_id,
                                          'monthly_pass')

    return {
        "ListItems": output
    }


@simulation_router.post("/oobeo/citation/{location_id}")
def secure_endpoint(request: dict,
                    authorization: str = Depends(AuthService.verify_authorization_oobeo),
                    ):

    data = {
        "data":{
            "status": "success",
            "id": "PYLSTpkUNm325zy1leHi"
        }
    }
    return data


@simulation_router.get("/get/{lpr}/{gracePeriod}")
def get_flowbird_data(
    lpr: str
):
    if lpr == 'ALB252':
        xml_data = """<ArrayOfValidParkingData xmlns="http://schema.caleaccess.com/cwo2exportservice/Enforcement/5/" xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
            <ValidParkingData>
                <Amount>8</Amount>
                <Article>
                    <Id>100</Id>
                    <Name>APBS1</Name>
                </Article>
                <Code>ALB252</Code>
                <ContainsTerminalOutOfCommunication i:nil="true"/>
                <DateChangedUtc>2025-04-07T17:05:21</DateChangedUtc>
                <DateCreatedUtc>2025-04-07T17:05:21</DateCreatedUtc>
                <EndDateUtc>2031-04-08T03:59:37</EndDateUtc>
                <IsExpired>false</IsExpired>
                <ParkingSpace i:nil="true"/>
                <ParkingZone i:nil="true"/>
                <PostPayment>
                    <PostPaymentNetworkName/>
                    <PostPaymentTransactionID i:nil="true"/>
                    <PostPaymentTransactionStatusKey i:nil="true"/>
                </PostPayment>
                <PurchaseDateUtc>2025-04-07T17:05:12</PurchaseDateUtc>
                <StartDateUtc>2025-04-07T17:02:37</StartDateUtc>
                <Tariff>
                    <Id>100</Id>
                    <Name>$4H$800MX</Name>
                </Tariff>
                <Terminal>
                    <Id>COURT</Id>
                    <Latitude>41.655520</Latitude>
                    <Longitude>-83.538736</Longitude>
                    <ParentNode>COURT LOT - PGM 1</ParentNode>
                </Terminal>
                <TicketNumber>43444</TicketNumber>
                <Zone>COURT</Zone>
            </ValidParkingData>
        </ArrayOfValidParkingData>"""

    elif lpr == 'ALB253':
        xml_data = """<ArrayOfValidParkingData xmlns="http://schema.caleaccess.com/cwo2exportservice/Enforcement/5/" xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
            <ValidParkingData>
                <Amount>9</Amount>
                <Article>
                    <Id>100</Id>
                    <Name>APBS1</Name>
                </Article>
                <Code>ALB253</Code>
                <ContainsTerminalOutOfCommunication i:nil="true"/>
                <DateChangedUtc>2025-04-07T17:05:21</DateChangedUtc>
                <DateCreatedUtc>2025-04-07T17:05:21</DateCreatedUtc>
                <EndDateUtc>2025-04-08T03:59:37</EndDateUtc>
                <IsExpired>false</IsExpired>
                <ParkingSpace i:nil="true"/>
                <ParkingZone i:nil="true"/>
                <PostPayment>
                    <PostPaymentNetworkName/>
                    <PostPaymentTransactionID i:nil="true"/>
                    <PostPaymentTransactionStatusKey i:nil="true"/>
                </PostPayment>
                <PurchaseDateUtc>2025-04-07T17:05:12</PurchaseDateUtc>
                <StartDateUtc>2025-04-07T17:02:37</StartDateUtc>
                <Tariff>
                    <Id>100</Id>
                    <Name>$4H$800MX</Name>
                </Tariff>
                <Terminal>
                    <Id>COURT</Id>
                    <Latitude>41.655520</Latitude>
                    <Longitude>-83.538736</Longitude>
                    <ParentNode>COURT LOT - PGM 1</ParentNode>
                </Terminal>
                <TicketNumber>43444</TicketNumber>
                <Zone>COURT</Zone>
            </ValidParkingData>
            <ValidParkingData>
                <Amount>10</Amount>
                <Article>
                    <Id>100</Id>
                    <Name>APBS1</Name>
                </Article>
                <Code>ALB253</Code>
                <ContainsTerminalOutOfCommunication i:nil="true"/>
                <DateChangedUtc>2025-04-08T17:05:21</DateChangedUtc>
                <DateCreatedUtc>2025-04-07T17:05:21</DateCreatedUtc>
                <EndDateUtc>2025-04-10T03:59:37</EndDateUtc>
                <IsExpired>false</IsExpired>
                <ParkingSpace i:nil="true"/>
                <ParkingZone i:nil="true"/>
                <PostPayment>
                    <PostPaymentNetworkName/>
                    <PostPaymentTransactionID i:nil="true"/>
                    <PostPaymentTransactionStatusKey i:nil="true"/>
                </PostPayment>
                <PurchaseDateUtc>2025-04-08T17:05:12</PurchaseDateUtc>
                <StartDateUtc>2025-04-08T17:02:37</StartDateUtc>
                <Tariff>
                    <Id>100</Id>
                    <Name>$4H$800MX</Name>
                </Tariff>
                <Terminal>
                    <Id>COURT</Id>
                    <Latitude>41.655520</Latitude>
                    <Longitude>-83.538736</Longitude>
                    <ParentNode>COURT LOT - PGM 1</ParentNode>
                </Terminal>
                <TicketNumber>43444</TicketNumber>
                <Zone>COURT</Zone>
            </ValidParkingData>
            <ValidParkingData>
                <Amount>11</Amount>
                <Article>
                    <Id>100</Id>
                    <Name>APBS1</Name>
                </Article>
                <Code>ALB253</Code>
                <ContainsTerminalOutOfCommunication i:nil="true"/>
                <DateChangedUtc>2025-04-08T17:05:21</DateChangedUtc>
                <DateCreatedUtc>2025-06-07T17:05:21</DateCreatedUtc>
                <EndDateUtc>2031-04-08T05:00:00</EndDateUtc>
                <IsExpired>false</IsExpired>
                <ParkingSpace i:nil="true"/>
                <ParkingZone i:nil="true"/>
                <PostPayment>
                    <PostPaymentNetworkName/>
                    <PostPaymentTransactionID i:nil="true"/>
                    <PostPaymentTransactionStatusKey i:nil="true"/>
                </PostPayment>
                <PurchaseDateUtc>2025-06-07T17:05:12</PurchaseDateUtc>
                <StartDateUtc>2025-04-10T03:59:37</StartDateUtc>
                <Tariff>
                    <Id>100</Id>
                    <Name>$4H$800MX</Name>
                </Tariff>
                <Terminal>
                    <Id>COURT</Id>
                    <Latitude>41.655520</Latitude>
                    <Longitude>-83.538736</Longitude>
                    <ParentNode>COURT LOT - PGM 1</ParentNode>
                </Terminal>
                <TicketNumber>43444</TicketNumber>
                <Zone>COURT</Zone>
            </ValidParkingData>
        </ArrayOfValidParkingData>"""
    else:
        return Response(status_code=status.HTTP_204_NO_CONTENT)


    return Response(content=xml_data.strip(), media_type="application/xml")
