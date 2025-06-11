import json
import logging
from collections import defaultdict
from typing import List

import requests
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from sqlalchemy.orm import Session
from starlette import status

from app import schema
from app.config import settings
from app.dependencies.deps import get_db
from app.models import base
from app.schema import CreateOrganizationSchema
from app.service import AuthService
from app.service.configure_lot_service import ConfigureLot
from app.utils import enum
from app.utils.common import api_response, update_without_replacement, custom_encoder, find_key_in_dict
from app.utils.security import verify_token

logger = logging.getLogger(__name__)
lot = APIRouter()


@lot.post('/v1/client')
def create_user(client_name: str = Form(), db: Session = Depends(get_db)):
    """
    Generate a New API Client
    """
    user = ConfigureLot.generate_client(client_name, db)
    user_schema = schema.UserSchema(id=user.id,
                                    username=user.user_name,
                                    client_id=user.client_id,
                                    client_secret=user.client_secret,
                                    created_at=user.created_at,
                                    updated_at=user.updated_at
                                    )
    return api_response(
        message="Successfully created.",
        status="success",
        data=[json.loads(json.dumps(user_schema.model_dump(), default=custom_encoder))],
        status_code=201
    )


@lot.post('/v1/token')
def generate_token(client_id: str = Form(),
                   client_secret: str = Form(),
                   org_id: int = Form(),
                   db: Session = Depends(get_db)):
    """
    Generate a token for api access
    """
    return api_response(
        message="Successfully generated.",
        status="success",
        data=[ConfigureLot.generate_access_token(db, client_id, client_secret, org_id)]
    )


@lot.get('/v1/parking-lot/{parking_lot_id}/verify')
def check_lot_existence(parking_lot_id: int,
                        token: base.User = Depends(verify_token),
                        db: Session = Depends(get_db)):
    """
    Verify the parking lot exists on sg-connect or not
    """
    try:
        data = ConfigureLot.verify_parking_lot(db, parking_lot_id)
        return api_response(
            message="Successfully verified.",
            status="success",
            data=[data]
        )
    except Exception as e:
        import logging
        from fastapi import HTTPException
        logger = logging.getLogger(__name__)
        logger.error(f"An error occurred: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@lot.post('/v1/org/lot/register', response_model=schema.OrgLotSchema, )
def add_org_and_parking_lot(create_connect_parking_lot_schema: schema.OrgLotSchema,
                            token: str = Depends(verify_token),
                            db: Session = Depends(get_db)):
    """
    Register the parking lot
    """
    from app.utils.common import default_connection_sg_admin
    org_data = create_connect_parking_lot_schema.dict(exclude={"parking_lots"})
    org_id = base.Organization.get_org(db, org_data['org_id'])

    if not org_id:
        organization = base.Organization.create(db, CreateOrganizationSchema(org_id=org_data['org_id'],
                                                                             org_name=org_data['org_name']))
    else:
        organization = org_id

    data = []
    message = ""

    for parking_lot in create_connect_parking_lot_schema.parking_lots:

        is_registered = base.ConnectParkinglot.get(db,
                                                   parking_lot.parking_lot_id
                                                   )
        if is_registered:
            message = "No new parking lots were registered. All provided parking lots are already registered."
            data.append(schema.ParkingLotSchema(parking_lot_id=is_registered.parking_lot_id,
                                                contact_email=is_registered.contact_email,
                                                contact_name=is_registered.contact_name,
                                                parking_lot_name=is_registered.parking_lot_name,
                                                grace_period=is_registered.grace_period,
                                                retry_mechanism=is_registered.retry_mechanism,
                                                is_in_out_policy=is_registered.is_in_out_policy).parking_lot_schema_to_dict())

            default_connection_sg_admin(db, is_registered.id)
            if not is_registered.parking_lot_name:
                is_registered.parking_lot_name = parking_lot.parking_lot_name

            db.commit()

            continue
        else:
            message = "Successfully registered the parking lot."
            parking_lot.organization_id = organization.id
            if not parking_lot.parking_lot_id:
                continue
            connect_parkinglot = ConfigureLot.add_parking_lot(parking_lot, db)
            if not connect_parkinglot:
                return api_response(
                    message="Parking lot not found.",
                    status="error",
                    status_code=404
                )

            default_connection_sg_admin(db, connect_parkinglot.id)
            db.commit()

            data.append(schema.ParkingLotSchema(parking_lot_id=connect_parkinglot.parking_lot_id,
                                                contact_email=connect_parkinglot.contact_email,
                                                contact_name=connect_parkinglot.contact_name,
                                                parking_lot_name=connect_parkinglot.parking_lot_name,
                                                grace_period=connect_parkinglot.grace_period,
                                                retry_mechanism=connect_parkinglot.retry_mechanism,
                                                is_in_out_policy=connect_parkinglot.is_in_out_policy).parking_lot_schema_to_dict()
                        )

    return api_response(
        message=message,
        status="success",
        status_code=201,
        data=data
    )


@lot.get('/v1/parking-lot/{parking_lot_id}')
def get_parkinglot_details(parking_lot_id: int,
                           token: base.User = Depends(verify_token),
                           db: Session = Depends(get_db)):
    """
    Get details of parking lot
    """
    connect_parkinglot = base.ConnectParkinglot.get(db, parking_lot_id)
    if not connect_parkinglot:
        return api_response(
            message="Parking lot not found.",
            status="error",
            status_code=404
        )
    connect_parkinglot_schema = schema.ParkingLotSchema(parking_lot_id=connect_parkinglot.parking_lot_id,
                                                        contact_email=connect_parkinglot.contact_email,
                                                        grace_period=connect_parkinglot.grace_period,
                                                        retry_mechanism=connect_parkinglot.retry_mechanism,
                                                        is_in_out_policy=connect_parkinglot.is_in_out_policy)
    spotgenius_url = settings.SPOT_GENIUS_API_BASE_URL
    parking_lot_info = None
    attempts = 0
    while attempts < 1:
        try:
            headers = {
                'Authorization': f'Bearer {token}'
            }
            response = requests.get(f'{spotgenius_url}/api/external/'
                                    f'v1/parking_lot/{connect_parkinglot.parking_lot_id}/lot_status',
                                    headers=headers)
            if response.status_code == 200:
                parking_lot_info = response.text
                print(parking_lot_info)
                attempts += 1
            elif response.status_code == 401:
                form_data = {
                    "client_id": "QnTio5aBsUWov0D407wxXdO4p1Mv4xmZ8wLx_73fiRg",
                    "client_secret": "Zcl97bgSPdItfNpVT3M7S5R5FaQVwTvvdT4gc_2_0CQ"
                }
                response = requests.post(f'{spotgenius_url}/api/oauth/token', data=form_data)
                if response.status_code == 200:
                    token = response.text
                    token = token.replace('"', '')
            else:
                attempts += 1
        except Exception as e:
            return api_response(
                message=f"Error: {str(e)}",
                status="error",
                status_code=400
            )

    data = json.loads(json.dumps(connect_parkinglot_schema.model_dump(), default=custom_encoder))
    if parking_lot_info:
        data = update_without_replacement(data, json.loads(parking_lot_info))

    return api_response(
        message="Successfully retrieved the parking lot details.",
        status="success",
        data=[data]
    )


@lot.patch('/v1/update/parking-lot')
def update_parking_lot(update_connect_parkinglot_schema: schema.UpdateLot,
                       token: str = Depends(verify_token),
                       db: Session = Depends(get_db)):
    """
    Update the Parking Lot
    """
    data = []
    organization = base.Organization.get_org(db, update_connect_parkinglot_schema.org_id)
    if not organization:
        organization_create_schema = schema.CreateOrganizationSchema(org_id=update_connect_parkinglot_schema.org_id)
        organization = base.Organization.create(db, organization_create_schema)

    for parking_lot_id in update_connect_parkinglot_schema.parking_lot:
        connect_parkinglot = base.ConnectParkinglot.get_parking_lot(db, parking_lot_id)
        if not connect_parkinglot:
            connect_parkinglot_schema = schema.CreateParkinglotSchema(
                parking_lot_id=parking_lot_id,
                contact_email=update_connect_parkinglot_schema.updated_properties.contact_email,
                organization_id=organization.id
            )
            base.ConnectParkinglot.create(db, connect_parkinglot_schema)

    base.Organization.update(db, organization.id, update_connect_parkinglot_schema.updated_properties)

    for parking_lot in organization.parking_lots:
        parking_lot_obj = base.ConnectParkinglot.get_parking_lot(db, parking_lot.parking_lot_id)

        if not parking_lot_obj:
            data.append({
                "message": f"Parking lot with ID {parking_lot.parking_lot_id} not found. Skipping update.",
                "status": "error"
            })
            continue

        updated_lot = ConfigureLot.update_parking_lot(db, parking_lot_obj.id,
                                                      update_connect_parkinglot_schema.updated_properties)

        if updated_lot:
            parking_lot_data = schema.UpdateParkingLotSchema(
                parking_lot_id=updated_lot.parking_lot_id,
                contact_email=updated_lot.contact_email,
                contact_name=updated_lot.contact_name,
                grace_period=updated_lot.grace_period,
                retry_mechanism=updated_lot.retry_mechanism,
                is_in_out_policy=updated_lot.is_in_out_policy
            ).parking_lot_schema_to_dict()

            violation_config = schema.ViolationConfigurationSchema(
                pricing_type=update_connect_parkinglot_schema.updated_properties.pricing_type.upper(),
                parking_lot_id=parking_lot_obj.id
            )

            base.ViolationConfiguration.create_or_update(db, violation_config)
            data.append(parking_lot_data)
        else:
            data.append({
                "message": f"Failed to update parking lot with ID {parking_lot.parking_lot_id}.",
                "status": "error"
            })

    # Add violation configuration to violation service
    ConfigureLot.upsert_violation_configuration(organization, update_connect_parkinglot_schema)

    return api_response(
        message="Successfully updated parking lot.",
        status="success",
        data=data
    )


@lot.get('/v1/event-types')
def get_all_events(token: str = Depends(verify_token), db: Session = Depends(get_db)):
    """
    Get all event types
    """
    event_types = ConfigureLot.get_events(db)
    data = []
    for event_type in event_types:
        event_type_schema = schema.EventTypesSchema(id=event_type.id,
                                                    text_key=event_type.text_key,
                                                    name=event_type.name,
                                                    created_at=event_type.created_at,
                                                    updated_at=event_type.updated_at)
        data.append(json.loads(json.dumps(event_type_schema.model_dump(), default=custom_encoder)))
    return api_response(
        message="Successfully retrieved event types.",
        status="success",
        data=data
    )


# @lot.get('/v1/provider/types')
# def get_provider_types(request: Request,
#                        db: Session = Depends(get_db),
#                        token: base.User = Depends(verify_token),
#                        ):
#     """
#     Get all provider types
#     """
#     organization_id = int(request.headers.get('organization'))
#     if not base.Organization.get_org(db, organization_id):
#         organization_create_schema = schema.CreateOrganizationSchema(org_id=organization_id)
#         base.Organization.create(db, organization_create_schema)
#
#     provider_types = ConfigureLot.get_provider_types(db)
#     data = []
#     for provider_type in provider_types:
#         provider_type_schema = schema.ProviderTypeSchema(id=provider_type.id,
#                                                          text_key=provider_type.text_key,
#                                                          name=provider_type.name,
#                                                          created_at=provider_type.created_at,
#                                                          updated_at=provider_type.updated_at)
#         data.append(json.loads(json.dumps(provider_type_schema.model_dump(), default=custom_encoder)))
#     return api_response(
#         message="Successfully retrieved provider types.",
#         status="success",
#         data=data
#     )


@lot.get('/v1/provider/types')
def get_provider_types(request: Request,
                       db: Session = Depends(get_db),
                       token: base.User = Depends(verify_token),
                       ):
    """
    Get all provider types
    """
    access_to_view_provider = AuthService.can_access_provider(request)
    organization_id = int(request.headers.get('organization'))
    if not base.Organization.get_org(db, organization_id):
        organization_create_schema = schema.CreateOrganizationSchema(org_id=organization_id)
        base.Organization.create(db, organization_create_schema)

    provider_types = ConfigureLot.get_provider_types(db)
    data = []
    org = base.Organization.get_org(db, int(request.headers.get('organization')))

    if org:
        parkinglot_org_id = base.ConnectParkinglot.lots_by_org_order_by_grace_period_contact_info(db, org.id)
        parking_lot_ids = [parking_lot.id for parking_lot in parkinglot_org_id]

        for provider_type in provider_types:
            provider_type_schema = schema.ProviderTypeSchema(id=provider_type.id,
                                                            text_key=provider_type.text_key,
                                                            name=provider_type.name,
                                                            created_at=provider_type.created_at,
                                                            updated_at=provider_type.updated_at
                                                            )

            provider_type_data = provider_type_schema.model_dump()
            filter_by = provider_type.text_key

            if parking_lot_ids:
                connected_providers = base.ProviderConnect.get_connected_provider(db, filter_by, parking_lot_ids, org, access_to_view_provider)

                if connected_providers:
                    provider_type_data.update(connected_providers.dict())

            data.append(json.loads(json.dumps(provider_type_data, default=custom_encoder)))

    return api_response(
        message="Successfully retrieved provider types.",
        status="success",
        data=data
    )


@lot.post('/v1/provider')
def create_provider(create_provider_schema: schema.CreateProviderSchema,
                    token: base.User = Depends(verify_token),
                    db: Session = Depends(get_db)):
    provider_type = base.ProviderTypes.get_by_id(db, create_provider_schema.provider_type_id)
    if not provider_type:
        return api_response(
            message="Provider type doesn't exists.",
            status="error",
            status_code=404
        )
    provider = ConfigureLot.create_provider(create_provider_schema, db)
    provider_schema = schema.ProviderSchema(id=provider.id,
                                            name=provider.name,
                                            text_key=provider.text_key,
                                            provider_type_id=provider.provider_type_id,
                                            created_at=provider.created_at,
                                            updated_at=provider.updated_at)
    data = json.loads(json.dumps(provider_schema.model_dump(), default=custom_encoder))
    return api_response(
        message="Successfully created.",
        status="success",
        data=data
    )


@lot.post('/v1/provider/creds')
def create_provider_creds(create_provider_schema: schema.GetProviderCredsSchema,
                          token: base.User = Depends(verify_token),
                          db: Session = Depends(get_db)):
    provider = base.Provider.get_by_id(db, create_provider_schema.provider_id)
    if not provider:
        return api_response(
            message="Provider doesn't exists.",
            status="error",
            status_code=404
        )

    # updated_key_value = create_provider_schema.model_dump()
    # updated_key_value['client_secret'] = encrypt_value(create_provider_schema.client_secret)
    # updated_schema = schema.CreateProviderCredsSchema(**updated_key_value)
    # for credential in create_provider_schema.credentials:

    provider_creds = ConfigureLot.create_provider_creds(db, create_provider_schema)

    return api_response(
        message="Successfully created provider creds.",
        status="success",
        data=provider_creds
    )


@lot.get('/v1/providers', response_model=List[schema.ProviderSchema])
def get_providers(db: Session = Depends(get_db),
                  token: str = Depends(verify_token)):
    return api_response(
        message="Successfully retrieved.",
        status="success",
        data=ConfigureLot.get_providers(db)
    )

@lot.get('/v1/get-parking-lot-provider-feature')
def get_lot_provider_feature(parking_lot_id: int,
                             db: Session = Depends(get_db),
                             token: str = Depends(verify_token)):
    return api_response(
        message="Successfully retrieved.",
        status="success",
        data=ConfigureLot.get_lot_provider_feature(db, parking_lot_id)
    )


@lot.get('/v1/get-provider-feature')
def get_lot_provider_feature(provider_id: int,
                             db: Session = Depends(get_db),
                             token: str = Depends(verify_token)):
    return api_response(
        message="Successfully retrieved.",
        status="success",
        data=ConfigureLot.get_provider_feature(db, provider_id)
    )


@lot.get('/v1/provider/support/{provider_id}')
def get_provider_support(provider_id: int,
                         token: base.User = Depends(verify_token),
                         db: Session = Depends(get_db)
                         ):
    provider = base.Provider.get_by_id(db, provider_id)
    if not provider:
        return api_response(
            message="Provider doesn't exists",
            status="error",
            data=[],
            status_code=404
        )

    provider_schema = schema.ProviderSchema(id=provider.id,
                                            name=provider.name,
                                            text_key=provider.text_key,
                                            api_endpoint=provider.api_endpoint,
                                            auth_type=provider.auth_type,
                                            logo=provider.logo,
                                            provider_type_id=provider.provider_type_id,
                                            created_at=provider.created_at,
                                            updated_at=provider.updated_at)
    provider_data = json.loads(json.dumps(provider_schema.model_dump(), default=custom_encoder))

    provider_type = base.ProviderTypes.get_by_id(db, provider.provider_type_id)

    provider_features_list = []
    provider_features = db.query(base.ProviderFeature).filter(base.ProviderFeature.provider_id == provider_id)
    for provider_feature in provider_features:
        feature = db.query(base.Feature).filter(base.Feature.id == provider_feature.feature_id).first()
        feature_schema = schema.FeatureSchema(id=feature.id,
                                              name=feature.name,
                                              text_key=feature.text_key,
                                              description=feature.description,
                                              created_at=feature.created_at,
                                              updated_at=feature.updated_at)
        feature_data = json.loads(json.dumps(feature_schema.model_dump(), default=custom_encoder))
        provider_features_list.append(feature_data)

    # provider_data.update({"provider_type": provider_type.name})
    provider_data.update({"features": provider_features_list})

    return api_response(
        message="Successfully retrieved.",
        status="success",
        data=provider_data
    )


@lot.get('/v1/features')
def get_all_features(db: Session = Depends(get_db),
                     token: base.User = Depends(verify_token)
                     ):
    """
    Get all features
    """
    features = ConfigureLot.get_all_features(db)
    data = []
    for feature in features:
        provider_type_schema = schema.FeatureSchema(id=feature.id,
                                                    text_key=feature.text_key,
                                                    name=feature.name,
                                                    feature_type=feature.feature_type,
                                                    is_enabled=feature.is_enabled,
                                                    description=feature.description,
                                                    created_at=feature.created_at,
                                                    updated_at=feature.updated_at)
        data.append(json.loads(json.dumps(provider_type_schema.model_dump(), default=custom_encoder)))
    return api_response(
        message="Successfully retrieved features.",
        status="success",
        data=data
    )


@lot.get('/v1/provider/feature')
def attach_feature(provider_feature_schema: schema.ProviderFeatureSchema, db: Session = Depends(get_db),
                   token: base.User = Depends(verify_token)):
    return api_response(
        message="Successfully retrieved.",
        status="success",
        data=[]
    )


@lot.post('/v1/provider/connect')
def provider_parkinglot_attach(provider_parkinglot_schema: schema.ProviderParkinglotSchema,
                               token: base.User = Depends(verify_token),
                               db: Session = Depends(get_db)):
    """Attach Provider With Parking Lot"""

    data = []
    for provider_connects in provider_parkinglot_schema.provider_connects:

        connect_parkinglot = base.ConnectParkinglot.get_by_id(db, provider_connects.parking_lot_id)
        provider_cred = base.ProviderCreds.get_by_id(db, provider_connects.provider_cred)
        if not connect_parkinglot and provider_cred:
            return api_response(
                message="Parking lot or Provider Cred doesn't exists",
                status="error",
                data=[],
                status_code=404
            )

        else:
            provider_connect = base.ProviderConnect.connect_provider_creds_with_lot(db, provider_connects.provider_cred,
                                                                                    connect_parkinglot.id,
                                                                                    provider_connects.facility_id)
            feature = schema.ParkinglotProviderFeatureCreateSchema(provider_connect_id=provider_connect.id,
                                                                   feature_id=base.Feature.get_by_text_key(
                                                                       db,
                                                                       provider_parkinglot_schema.feature
                                                                   ).id)
            lot_provider_feature = base.ParkinglotProviderFeature.create(db, feature)
            data.append(lot_provider_feature.to_dict())

    return api_response(
        message="Successfully attached.",
        status="success",
        data=data
    )


@lot.put('/v1/provider/connect')
def provider_connect_update(update_parkinglot_schema: schema.ProviderConnectSchema,
                            token: base.User = Depends(verify_token),
                            db: Session = Depends(get_db)):
    """Update Provider With Parking Lot or Feature Update"""
    if update_parkinglot_schema.connect_parkinglot_id:
        connect_parkinglot = base.ConnectParkinglot.get_by_id(db, update_parkinglot_schema.connect_parkinglot_id)
        if not connect_parkinglot:
            return api_response(
                message="Parking lot doesn't exists",
                status="error",
                data=[],
                status_code=404
            )
    return api_response(
        message="Successfully updated.",
        status="success",
        data=[]
    )


@lot.post('/v1/provider/connect/attach-feature')
def attach_feature_with_parkinglot(attach_feature_schema: schema.AttachFeatureSchema,
                                   token: base.User = Depends(verify_token),
                                   db: Session = Depends(get_db)):
    """
    Attach Feature With Parking Lot.
    """
    data = []
    for parking_lot_provider_feature in attach_feature_schema.parking_lot_provider_features:

        provider_connect = base.ProviderConnect.get_by_id(db, parking_lot_provider_feature.provider_connect_id)
        if not provider_connect:
            return api_response(
                message="Provider not attached with this parking lot",
                status="error",
                data=[],
                status_code=404
            )
        feature__id = base.Feature.get_by_text_key(db, parking_lot_provider_feature.feature_id).id
        data.append(base.ParkinglotProviderFeature.create(db,
                                                          schema.ParkinglotProviderFeatureCreateSchema(
                                                              provider_connect_id=parking_lot_provider_feature.provider_connect_id,
                                                              feature_id=feature__id)).to_dict())

        return api_response(
            message="Successfully attached feature with parking lot.",
            status="success",
            data=data
        )


@lot.delete('/v1/provider/connect/{parking_lot_id}/{provider_id}/{feature_id}')
def detach_feature_with_parkinglot(parking_lot_id: int,
                                   provider_id: int,
                                   feature_id: int,
                                   token: base.User = Depends(verify_token),
                                   db: Session = Depends(get_db)):
    """
    Detaching Feature With Parking Lot.
    """
    feature = base.Feature.get(db, feature_id)
    if not feature:
        return api_response(
            message="Feature doesn't exists",
            status="error",
            data=[],
            status_code=404
        )
    provider_creds = base.ProviderCreds.get_by_provider(db, provider_id)
    if not provider_creds:
        return api_response(
            message="No Feature available to detach",
            status="error",
            data=[],
            status_code=404
        )
    for provider_cred in provider_creds:
        provider_connect = base.ProviderConnect.get_provider_connect(db, parking_lot_id, provider_cred.id)
        if not provider_connect:
            return api_response(
                message="Provider doesn't attached with this parking lot.",
                status="error",
                data=[],
                status_code=404
            )
        parkinglot_provider_feature = base.ParkinglotProviderFeature.detach_parkinglot_feature(db, feature_id,
                                                                                               provider_connect.id)
    data = []

    return api_response(
        message="Successfully detached feature with parking lot.",
        status="success",
        data=data
    )


@lot.get('/v1/provider/connect/{parking_lot_id}')
def provider_connect_with_parkinglot(parking_lot_id: int,
                                     token: base.User = Depends(verify_token),
                                     db: Session = Depends(get_db)):
    """
    Retrieve the connected provider for parking lot.
    """
    data = []
    provider_connects = db.query(base.ProviderConnect).filter(base.ProviderConnect.connect_id == parking_lot_id)
    if not provider_connects.all():
        return api_response(
            message="Provider Connect for this Parking lot doesn't exists",
            status="error",
            data=[],
            status_code=404
        )
    connect_parkinglot = base.ConnectParkinglot.get_by_id(db, parking_lot_id)
    if not connect_parkinglot:
        return api_response(
            message="Parking lot doesn't exists",
            status="error",
            data=[],
            status_code=404
        )
    connect_parkinglot_schema = schema.ParkingLotSchema(parking_lot_id=connect_parkinglot.parking_lot_id,
                                                        contact_email=connect_parkinglot.contact_email,
                                                        grace_period=connect_parkinglot.grace_period,
                                                        retry_mechanism=connect_parkinglot.retry_mechanism,
                                                        is_in_out_policy=connect_parkinglot.is_in_out_policy)

    connect_parkinglot_data = json.loads(json.dumps(connect_parkinglot_schema.model_dump(), default=custom_encoder))

    provider_creds_list = []
    for provider_connect in provider_connects:
        provider_cred = db.query(base.ProviderCreds).filter(
            base.ProviderCreds.id == provider_connect.provider_creds_id).first()
        provider_cred_schema = schema.ProviderCredsSchema(id=provider_cred.id,
                                                          text_key=provider_cred.text_key,
                                                          client_id=provider_cred.client_id,
                                                          access_token=provider_cred.access_token,
                                                          expire_time=provider_cred.expire_time,
                                                          provider_id=provider_cred.provider_id,
                                                          created_at=provider_cred.created_at,
                                                          updated_at=provider_cred.updated_at)
        provider_cred_data = json.loads(json.dumps(provider_cred_schema.model_dump(), default=custom_encoder))

        provider = db.query(base.Provider).filter(base.Provider.id == provider_cred.provider_id).first()
        provider_schema = schema.ProviderSchema(id=provider.id,
                                                name=provider.name,
                                                text_key=provider.text_key,
                                                api_endpoint=provider.api_endpoint,
                                                auth_type=provider.auth_type,
                                                logo=provider.logo,
                                                provider_type_id=provider.provider_type_id,
                                                created_at=provider.created_at,
                                                updated_at=provider.updated_at)
        provider_data = json.loads(json.dumps(provider_schema.model_dump(), default=custom_encoder))

        provider_cred_data.update({"provider": provider_data})
        provider_creds_list.append(provider_cred_data)

    connect_parkinglot_data.update({"providers_creds": provider_creds_list})

    data.append(connect_parkinglot_data)
    return api_response(
        message="Successfully retrieved the connected providers for parking lot.",
        status="success",
        data=data
    )


@lot.delete('/v1/detach-parking-lots')
def detach_provider_with_parkinglot(data_to_delete: schema.DeleteConnection,
                                    token: base.User = Depends(verify_token),
                                    db: Session = Depends(get_db)):
    """
    Detach Provider With Parking Lot
    """
    successful_deletions = []
    failed_deletions = []

    for delete in data_to_delete.deletions:
        provider_connect = base.ProviderConnect.detach_parking_lot(db, delete.provider_cred_id, delete.parking_lot_id)
        if provider_connect:
            successful_deletions.append({
                "provider_cred_id": delete.provider_cred_id,
                "parking_lot_id": delete.parking_lot_id,
                "status": "success"
            })
        else:
            failed_deletions.append({
                "provider_cred_id": delete.provider_cred_id,
                "parking_lot_id": delete.parking_lot_id,
                "status": "error",
                "message": "Provider doesn't attached with this parking lot."
            })
    if failed_deletions:
        return api_response(
            message="Some providers were not detached from their parking lots.",
            status="partial_success",
            data={"successes": successful_deletions, "failures": failed_deletions},
            status_code=200
        )

    return api_response(
        message="Successfully detached all providers with their parking lots.",
        status="success",
        data=successful_deletions,
        status_code=200
    )


@lot.get('/v1/provider/types/{provider_type_id}')
def get_providers_with_provider_type(provider_type_id: int,
                                     request: Request,
                                     # token: base.User = Depends(verify_token),
                                     db: Session = Depends(get_db)):
    """
    Get Providers with Provider Type
    """

    access_to_view_provider = AuthService.can_access_provider(request)

    connected_lot_ids = []
    provider_type = base.ProviderTypes.get_by_id(db, provider_type_id)
    if not provider_type:
        return api_response(
            message="Provider Type doesn't exists",
            status="error",
            data=[],
            status_code=404
        )

    provider_type_schema = schema.ProviderTypeSchema(id=provider_type.id,
                                                     text_key=provider_type.text_key,
                                                     name=provider_type.name,
                                                     created_at=provider_type.created_at,
                                                     updated_at=provider_type.updated_at)
    data = json.loads(json.dumps(provider_type_schema.model_dump(), default=custom_encoder))

    providers = base.Provider.get_specific_provider(db, provider_type_id, access_to_view_provider)
    providers_list = []

    for provider in providers:
        credentials = {}
        if provider.meta_data is not None:

            keys = ['global_level_config', 'parking_lot_level_config', 'customer_level_config']
            credentials = {key: find_key_in_dict(provider.meta_data, key) for key in keys}

            org_id = base.Organization.get_org(db, int(request.headers.get('organization')))
            if org_id:
                connected_lot_ids = base.ProviderConnect.get_provider_with_org_and_parking_lot(db, org_id.id,
                                                                                               provider.id)

        provider_schema = schema.ProviderSchema(id=provider.id,
                                                name=provider.name,
                                                text_key=provider.name,
                                                api_endpoint=provider.api_endpoint,
                                                auth_type=provider.auth_type,
                                                auth_level=provider.auth_level,
                                                logo=provider.logo,
                                                provider_type_id=provider.provider_type_id,
                                                credentials=credentials,
                                                connected_parking_lots=connected_lot_ids,
                                                created_at=provider.created_at,
                                                updated_at=provider.updated_at)
        provider_data = json.loads(json.dumps(provider_schema.model_dump(), default=custom_encoder))

        features = base.Feature.get_enabled_feature_by_provider_id(db, provider.id)
        features_list = []
        for feature in features:
            feature_schema = schema.FeatureSchema(id=feature.id,
                                                  name=feature.name,
                                                  text_key=feature.text_key,
                                                  description=feature.description,
                                                  feature_type=feature.feature_type,
                                                  is_enabled=feature.is_enabled,
                                                  created_at=feature.created_at,
                                                  updated_at=feature.updated_at)
            feature_data = json.loads(json.dumps(feature_schema.model_dump(), default=custom_encoder))
            features_list.append(feature_data)

        provider_data.update({"features": features_list})
        providers_list.append(provider_data)

    data.update({'providers': providers_list})

    return api_response(
        message="Successfully retrieved provider type details.",
        status="success",
        data=data
    )


@lot.post('/v1/attach/parkinglot/feature/event')
def attach_event_with_parkinglot(attach_event_with_pfeature: schema.AttachEventParkingFeature,
                                 token: base.User = Depends(verify_token),
                                 db: Session = Depends(get_db)):
    data = []
    for feature_event_type in attach_event_with_pfeature.feature_event_types:
        provider = base.Provider.get_by_id(db, feature_event_type.provider_id)
        if not provider:
            return api_response(
                message="Provider doesn't exists.",
                status="error",
                status_code=404
            )

        p_provider_feature = base.ParkinglotProviderFeature.get(db, feature_event_type.parkinglot_provider_feature_id)
        if p_provider_feature:
            provider_feature = base.ProviderFeature.get_provider_feature(db, feature_event_type.provider_id,
                                                                         p_provider_feature.feature_id)
            if not provider_feature:
                provider_feature_create_schema = (schema.
                                                  ProviderFeatureCreateSchema(feature_id=p_provider_feature.feature_id,
                                                                              provider_id=feature_event_type.provider_id))
                provider_feature = base.ProviderFeature.create(db, provider_feature_create_schema)

            event_feature = base.EventFeature.get_feature_event(db, provider_feature.feature_id)
            if not event_feature:
                return api_response(
                    message="Event Feature doesn't exists",
                    status="error",
                    data=[],
                    status_code=404
                )
            feature_url = base.FeatureUrlPath.get_by_provider_feature_id(db, provider_feature.id)
            if not feature_url:
                return api_response(
                    message="Feature url doesn't exists",
                    status="error",
                    data=[],
                    status_code=404
                )
            feature_url_id = feature_url.id

            feature_evnet_type = (base.FeatureEventType.
                                  get_attached_feature_event_type(db,
                                                                  event_feature.event_type_id,
                                                                  feature_url_id,
                                                                  feature_event_type.parkinglot_provider_feature_id))
            if not feature_evnet_type:
                feature_event = schema.FeatureEventType(event_type_id=event_feature.event_type_id,
                                                        parkinglot_provider_feature_id=p_provider_feature.id,
                                                        feature_url_path_id=feature_url_id).exclude_key(['provider_id'])
                data.append(base.FeatureEventType.create(db, feature_event).to_dict())

            return api_response(
                message="Successfully attach event with parking lot.",
                status="success",
                data=data
            )


@lot.get('/v1/provider/payment/config/{provider_id}/{org_id}')
def get_payment_provider_config(provider_id: int,
                                org_id: int,
                                features: str = Query(...),
                                token: base.User = Depends(verify_token),
                                db: Session = Depends(get_db)):
    """
    Get payment provider configuration details based on provider_id, feature_id, and org_id.
    """
    try:
        features = [int(feature_id) for feature_id in features.split(',')]
    except:
        features = json.loads(features)

    provider = base.Provider.get_by_id(db, provider_id)
    if not provider:
        return api_response(
            message="Provider doesn't exists",
            status="error",
            data=[],
            status_code=404
        )

    feature_id = None
    if provider.name.lower() == 'tiba' or provider.name.lower().startswith('oobeo'):
        provider_data, feature_data, parking_lots = ConfigureLot.get_payment_provider_config_service(db, provider,
                                                                                                     features, org_id)
    else:
        feature_id = features[0]

        feature = base.Feature.get(db, feature_id)
        if not feature:
            return api_response(
                message="Feature doesn't exists",
                status="error",
                data=[],
                status_code=404
            )

        provider_schema = schema.ProviderSchema(id=provider.id,
                                                name=provider.name,
                                                text_key=provider.text_key,
                                                api_endpoint=provider.api_endpoint,
                                                auth_type=provider.auth_type,
                                                provider_type_id=provider.provider_type_id,
                                                logo=provider.logo,
                                                auth_level=provider.auth_level,
                                                created_at=provider.created_at,
                                                updated_at=provider.updated_at)

        feature_schema = schema.FeatureSchema(id=feature.id,
                                              text_key=feature.text_key,
                                              name=feature.name,
                                              description=feature.description,
                                              feature_type=feature.feature_type,
                                              is_enabled=feature.is_enabled,
                                              created_at=feature.created_at,
                                              updated_at=feature.updated_at)

        provider_data = json.loads(provider_schema.model_dump_json())
        feature_data = json.loads(feature_schema.model_dump_json())

        provider_connects = base.ProviderConnect.get_provider_connects(db, provider_id, feature_id, org_id)

        connected_provider_connects = []
        for provider_connect in provider_connects:
            feature_event_types = base.FeatureEventType.get_all_by_provider_connect_and_feature(db, provider_connect.id,
                                                                                                feature.id)
            if feature_event_types:
                connected_provider_connects.append(provider_connect)

        grouped_by_parking_lot = defaultdict(list)
        for provider_connect in connected_provider_connects:
            grouped_by_parking_lot[provider_connect.connect_id].append(provider_connect)

        parking_lots = []
        for parking_lot, grouped_provider_connect in grouped_by_parking_lot.items():
            provider_connect_data = grouped_provider_connect[0]
            parking_lot = base.ConnectParkinglot.get_connect_parkinglot(db, provider_connect_data.connect_id)
            parkinglot_schema = schema.ParkingLotFullSchema(
                id=parking_lot.id,
                parking_lot_id=parking_lot.parking_lot_id,
                contact_email=parking_lot.contact_email,
                contact_name=parking_lot.contact_name,
                parking_lot_name=parking_lot.parking_lot_name,
                grace_period=parking_lot.grace_period,
                retry_mechanism=parking_lot.retry_mechanism,
                is_in_out_policy=parking_lot.is_in_out_policy,
                organization_id=parking_lot.organization_id,
                created_at=parking_lot.created_at,
                updated_at=parking_lot.updated_at
            )
            parking_lot_dict = parkinglot_schema.model_dump()

            provider_creds = base.ProviderCreds.get_by_id(db, provider_connect_data.provider_creds_id)
            provider_creds_schema = schema.ProviderCredsResponseSchema(
                id=provider_creds.id,
                text_key=provider_creds.text_key,
                client_id=provider_creds.client_id,
                provider_id=provider_creds.provider_id,
                meta_data=provider_creds.meta_data,
                created_at=provider_creds.created_at,
                updated_at=provider_creds.updated_at
            )

            provider_creds_data = json.loads(provider_creds_schema.model_dump_json())

            configuration_settings = provider.meta_data.get('configuration_settings')

            if provider.auth_level == enum.AuthLevel.PARKING_LOT.value:
                configuration_settings = ConfigureLot.get_provider_meta_data_with_values(provider,
                                                                                         provider_creds_data,
                                                                                         provider_creds,
                                                                                         provider_connect_data)

                if provider.name.lower() == 'tiba':
                    provider_data['credentials'] = configuration_settings
                    provider_data['provider_creds'] = provider_creds_data

                parking_lot_dict['credentials'] = configuration_settings
                parking_lot_dict['provider_creds'] = provider_creds_data
            else:
                configuration_settings = ConfigureLot.get_provider_meta_data_with_values(provider,
                                                                                         provider_creds_data,
                                                                                         provider_creds)

                provider_data['credentials'] = configuration_settings
                provider_data['provider_creds'] = provider_creds_data

                if provider.meta_data.get(enum.ConfigLevel.PARKING_LOT.value):
                    parking_lot_dict['provider_creds'] = provider_creds_data
                    parking_lot_dict['credentials'] = configuration_settings

            parking_lots.append(json.loads(json.dumps(parking_lot_dict, default=custom_encoder)))

    return api_response(
        message="Successfully retrieved payment provider config details",
        status="success",
        data=[
            {
                "provider": provider_data,
                "feature": feature_data,
                "parking_lots": parking_lots
            }
        ]
    )


@lot.get("/v1/provider/details")
def get_connected_providers(filter_by: str,
                            request: Request,
                            token: base.User = Depends(verify_token),
                            db: Session = Depends(get_db),
                            ):
    data = []
    access_to_view_provider = AuthService.can_access_provider(request)
    try:

        org = base.Organization.get_org(db, int(request.headers.get('organization')))
        if org:
            parkinglot_org_id = base.ConnectParkinglot.get_by_parkinglot_org_id(db, org.id)
            parking_lot_ids = [parking_lot.id for parking_lot in parkinglot_org_id]
            if parking_lot_ids:
                connected_providers = base.ProviderConnect.get_connected_provider(db, filter_by, parking_lot_ids, org, access_to_view_provider)

                if connected_providers:
                    data.append(connected_providers.dict())

        # Return a successful response even if not data with the connected providers data
        return api_response(
            message="Successfully fetched the connected providers",
            status="success",
            data=data
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"An error occurred while fetching connected providers: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while fetching connected providers")


@lot.post("/v1/connect/feature/provider/cred")
def feature_provider_cred_lot_mapping(creds_schema: schema.ConnectFeatureProviderCred,
                                      request: Request,
                                      token: base.User = Depends(verify_token),
                                      db: Session = Depends(get_db)):
    try:
        org = base.Organization.get_org(db, int(request.headers.get('organization')))
        processed_data, skipped_parking_lots = ConfigureLot.feature_provider_cred_lot_mapping_service(db,
                                                                                                      creds_schema,
                                                                                                      org)
        return api_response(
            message="Successfully connected",
            status="success",
            data={"processed_data": processed_data,
                "skipped_parking_lots": skipped_parking_lots}
        )
    except Exception as e:
        logger.error(f"Error in feature_provider_cred_lot_mapping: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error in create provide credentials"
        )

@lot.patch("/v1/update/cred")
def update_creds(update_creds_schema: schema.NewConfigSettings,
                 request: Request,
                 token: base.User = Depends(verify_token),
                 db: Session = Depends(get_db)):

    org = base.Organization.get_org(db, int(request.headers.get('organization')))
    ConfigureLot.cred_update_service(db, update_creds_schema, org)
    return api_response(
        message="Successfully Updated",
        status="success",
        data=[]
    )
