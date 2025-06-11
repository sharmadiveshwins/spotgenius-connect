from datetime import datetime, timedelta
import logging
import json
from typing import Any, Dict, Union, List
from collections import defaultdict
from fastapi import HTTPException
from redis import credentials
from starlette import status
from app import schema
from app.config import settings
from app.models import base
from app.schema import ConfigSettingsGlobal, ConfigSettingsNonGlobal
from app.service.violation_rest_service import violation_service
from app.utils import enum
from app.utils.common import api_response, custom_encoder
from app.utils.enum import Scope, ViolationType
from app.utils.security import create_jwt_token, encrypt_value, decrypt_encrypted_value
from app.service import AuthService
from app.service.payment_cred_sync import payment_service

logger = logging.getLogger()


class ConfigureLot:

    @staticmethod
    def generate_client(client_name: str, db):
        client = base.User.generate_new(db, client_name)
        return client

    @staticmethod
    def generate_access_token(db, client_id: str, client_secret: str, org_id: int):
        try:
            logger.info(f"Request token for client_id: {client_id} and client_secret: {client_secret}")
            client = base.User.authenticate_user(client_id, client_secret, db)
            if client is None:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid token request")
            expire_time = datetime.utcnow() + timedelta(hours=1)
            request = {
                "client_id": client_id,
                "org_id": org_id
            }
            token = create_jwt_token(request, expire_time)
            return {'token': token}
        except Exception as e:
            logger.error(f"An error occurred during login: {e}")
            raise e

    @staticmethod
    def add_parking_lot(request, db):
        lot = base.ConnectParkinglot.insert_parking_lot_id(db, request.model_dump())
        return lot

    @staticmethod
    def get_parking_lot_details(db, parking_lot_id):
        lot = base.ConnectParkinglot.get_parking_lot(db, parking_lot_id)
        if not lot:
            raise f'not found'
        return lot

    @staticmethod
    def get_provider_types(db):
        provider_types = base.ProviderTypes.get_all_provider_types(db)
        return provider_types

    @staticmethod
    def get_events(db):
        events = base.EventTypes.get_all_events(db)
        return events

    @staticmethod
    def update_parking_lot(db, parking_lot_id, to_update):
        update = base.ConnectParkinglot.update(db, parking_lot_id, to_update)
        if update:
            return update

    @staticmethod
    def create_provider(request, db):
        provider = base.Provider.create(db, request)
        return provider

    @staticmethod
    def get_providers(db):
        providers = base.Provider.get_all_providers(db)
        all_provider = []
        for provider in providers:
            all_provider.append(schema.ProviderSchema(name=provider.name,
                                                      text_key=provider.text_key,
                                                      logo=provider.logo,
                                                      provider_type=base.ProviderTypes.get_by_id(db,
                                                                                                 provider.provider_type_id).name)
                                )

        return all_provider

    @staticmethod
    def get_lot_providers(db, lot_id, provider_type):
        providers = base.Provider.get_lot_connected_providers(db, lot_id, provider_type)
        lot_provider = []
        for provider in providers:
            lot_provider.append({
                "id": provider["id"],
                "name": provider["name"]
            })

        return lot_provider

    @staticmethod
    def get_lot_provider_feature(db, parking_lot_id):
        lot = base.ConnectParkinglot.get_parking_lot(db, parking_lot_id)
        if not lot:
            raise f'parking lot is not register with id {parking_lot_id}'
        providers = base.ProviderConnect.get_provider_feature(db, lot.id)
        # TODO Response Enhancement
        return providers

    @staticmethod
    def get_provider_feature(db, provider_id):
        provider = base.Provider.get_provider_by_id(db, provider_id)
        if not provider:
            raise f'provider not register with id {provider_id}'

        provider_feature = base.FeatureUrlPath.get_feature_by_provider_id(db, provider.id)
        return provider_feature

    @staticmethod
    def verify_parking_lot(db, parking_lot: int):
        parking_lot = base.ConnectParkinglot.get_parking_lot(db, parking_lot)
        is_exist = bool(parking_lot)
        return {"is_parking_lot_exist": is_exist}

    @staticmethod
    def get_all_features(db):
        return base.Feature.get_all_features(db)

    @staticmethod
    def feature_provider_cred_lot_mapping_service(db, request: schema.ConnectFeatureProviderCred, org):

        meta_data = {}
        filtered_config_settings = []
        skipped_parking_lots = []
        meta_data_list = []

        features = request.features

        enforcement_inactivate_feature = base.ProviderFeature.check_enforcement_inactivate_feature(db,
                                                                                                   request.provider_id)
        if enforcement_inactivate_feature:
            features.append(enforcement_inactivate_feature.id)
        for config_setting in request.config_settings:
            credentials_dict = {cred.key: int(cred.value) if cred.type == 'number' else cred.value for cred in
                                config_setting.credentials}

            if not isinstance(config_setting, (schema.ConfigSettingsGlobal, schema.ConfigSettingsNonGlobal)):\
                raise TypeError("Each item in config_settings should be an instance of ConfigSettingsGlobal "
                                "or ConfigSettingsNonGlobal")

            #  Handle ConfigSettingsGlobal
            if isinstance(config_setting, schema.ConfigSettingsGlobal):
                new_parking_lot_list = []
                for parking_lot_id in config_setting.parking_lot:

                    parking_lot_pk = base.ConnectParkinglot.get_connect_parking_lot_id(db, parking_lot_id)

                    if not parking_lot_pk:
                        skipped_parking_lots.append(parking_lot_id)
                        continue

                    existing_provider_connect = base.ProviderConnect.is_associate(db, parking_lot_pk.id,
                                                                                  request.provider_id,
                                                                                  request.feature_id)
                    if existing_provider_connect:
                        continue
                    new_parking_lot_list.append(parking_lot_id)

                if new_parking_lot_list:
                    new_config_setting = schema.ConfigSettingsGlobal(
                        parking_lot=new_parking_lot_list,
                        credentials=config_setting.credentials,
                        meta_data=config_setting.meta_data,
                        cred_id=config_setting.cred_id
                    )
                    filtered_config_settings.append(new_config_setting)

            # Handle ConfigSettingsNonGlobal
            elif isinstance(config_setting, schema.ConfigSettingsNonGlobal):
                parking_lot_obj = base.ConnectParkinglot.get_connect_parking_lot_id(db, config_setting.parking_lot)
                existing_provider_connect = base.ProviderConnect.is_associate(db, parking_lot_obj.id,
                                                                              request.provider_id,
                                                                              request.feature_id)
                if existing_provider_connect:
                    continue  # Skip the already connected parking lot
                filtered_config_settings.append(config_setting)

            if meta_data:
                # meta_data_list.append(config_setting.meta_data)
                meta_data_list.append(credentials_dict)
            else:
                meta_data.update(credentials_dict)
                meta_data_list.append(meta_data)

        if not filtered_config_settings:
            logger.info("All provided parking lots are already associated or not registered yet")
            return api_response(message="All provided parking lots are already associated or not registered yet.",
                                status="skipped",
                                status_code=200,
                                data={"skipped_parking_lots": skipped_parking_lots}
                                )


        if len(meta_data_list) > 1:
            conf_setting = schema.GetProviderCredsSchema(config_settings=filtered_config_settings,
                                                         meta_data=meta_data,
                                                         meta_data_list=meta_data_list)
        else:
            conf_setting = schema.GetProviderCredsSchema(config_settings=filtered_config_settings,
                                                         meta_data=meta_data)

        creds = ConfigureLot.create_provider_creds(db, request.provider_id, conf_setting)

        processed_data = []
        bulk_payment_creds = []

        if enforcement_inactivate_feature and creds:
            creds.append(creds[0].copy())

        for cred in creds:
            try:
                lot = base.ConnectParkinglot.get_by_id(db, cred['parking_lot_id'])
                if lot.organization_id != org.id:
                    lot.organization_id = org.id
                provider_connect = base.ProviderConnect.connect_provider_creds_with_lot(db,
                                                                                        cred['provider_cred_id'],
                                                                                        cred['parking_lot_id'],
                                                                                        facility_id=cred[
                                                                                            'facility_id'] if cred[
                                                                                            'facility_id'] else str(
                                                                                            54861))
                for feature_id in features:
                    parking_lot_provider_feature = schema.ParkinglotProviderFeatureCreateSchema(
                        provider_connect_id=provider_connect.id,
                        feature_id=feature_id)

                    lot_provider_feature = base.ParkinglotProviderFeature.create(db, parking_lot_provider_feature)

                    # event_features = base.EventFeature.get_feature_event(db, feature_id)
                    event_features = base.EventFeature.get_feature_events(db, feature_id)
                    for event_feature in event_features:

                        # prevent to configure overstay violation event type if parkinglot havn't Non-payment hour window
                        if lot.parking_operations == enum.ParkingOperations.paid_24_hours.value:
                            event_type = base.EventTypes.get_by_id(db, event_feature.event_type_id)
                            if event_type.text_key == enum.EventTypes.OVERSTAY_VIOLATION.value:
                                continue

                        provider_feature = base.ProviderFeature.get_provider_feature(db, request.provider_id,
                                                                                    feature_id)
                        if not provider_feature:
                            raise ValueError('Payment verification method not available with this provider')

                        feature_url_path = base.FeatureUrlPath.get_by_provider_feature_id(db, provider_feature.id)
                        feature_event_type = schema.FeatureEventType(event_type_id=event_feature.event_type_id,
                                                                    feature_url_path_id=feature_url_path.id,
                                                                    parkinglot_provider_feature_id=lot_provider_feature.id).exclude_key(
                            ['provider_id'])
                        created_feature_event_type = base.FeatureEventType.create(db, feature_event_type).to_dict()
                        processed_data.append(created_feature_event_type)

                        feature_obj = base.Feature.get(db, request.feature_id)

                        if feature_obj and feature_obj.feature_type == enum.FeatureType.PAYMENT:
                            provider_creds = base.ProviderConnect.get_full_provider_creds(db, connect_id=cred["parking_lot_id"], provider_creds_id=cred["provider_cred_id"])
                            if provider_creds["feature_type_key"] == enum.Feature.PAYMENT_CHECK_SPOT.value:
                                feature = "spot"
                            else:
                                feature = "lpr"
                            bulk_payment_creds.append({
                                "client_id": provider_creds["client_id"],
                                "client_secret": provider_creds["client_secret"],
                                "provider": provider_creds["provider_name"],
                                "feature": feature,
                                "api_key": provider_creds["api_key"],
                                "meta_data": provider_creds["meta_data"],
                                "parking_lot_id": provider_creds["parking_lot_id"],
                                "org_id": org.org_id,
                                "provider_type": enum.FeatureType.PAYMENT.value,
                                "facility_id": provider_creds["facility_id"] if provider_creds["facility_id"] else None,
                                "tags": provider_creds["meta_data"].get("tags", ["SG"])
                            })

            except Exception as e:
                db.rollback()
                bulk_payment_creds = []
                logger.info(f"Failed to process parking lot with ID {cred['parking_lot_id']}: {str(e)}")

                processed_data.append({
                    "message": f"Failed to process parking lot with ID {cred['parking_lot_id']}: {str(e)}",
                    "status": "error"
                })


        # CALL_PAYMENT_SERVICE_START
        if bulk_payment_creds:
            try:
                payment_response = ConfigureLot.create_provider_instances_bulk(bulk_payment_creds)
                for res in (payment_response or []):
                    if res.get("status") == "error":
                        processed_data.append(res)
            except Exception as e:
                db.rollback()
                logger.error(f"Bulk PaymentService failed: {str(e)}")
                for cred in bulk_payment_creds:
                    processed_data.append({
                        "message": f"Failed to call PaymentService for lot {cred['parking_lot_id']}: {str(e)}",
                        "status": "error"
                    })
        # CALL_PAYMENT_SERVCE_END
        db.commit()
        return processed_data, skipped_parking_lots

    @staticmethod
    def create_provider_creds(db, provider_id: int, request_data: schema.GetProviderCredsSchema):

        """
        Description:
        """

        global parking_lot
        data = []
        provider = base.Provider.get_provider_by_id(db, provider_id)
        create_creds = schema.CreateProviderCredsSchema(
            provider_id=provider_id,
        )

        for index, configurations in enumerate(request_data.config_settings):
            facility_id = ""
            p_type = base.ProviderTypes.get_by_id(db, provider.provider_type_id)
            if provider.name.lower() == 'tiba':
                text_key = f"{enum.ProviderTypes.PROVIDER_RESERVATION.value}.{provider.name.lower()}"
            else:
                text_key = f"{p_type.text_key}.{provider.name.lower()}"

            create_creds.text_key = text_key
            create_creds.meta_data = configurations.meta_data
            ConfigureLot.reset_attributes(create_creds, exclude=['provider_id', 'text_key'])

            for credential in configurations.credentials:
                if hasattr(create_creds, credential.key):
                    if credential.type and credential.type == enum.ProviderConfigurationDataType.MASKED.value:
                        setattr(create_creds, credential.key, encrypt_value(credential.value))
                    else:
                        setattr(create_creds, credential.key, credential.value)
                if credential.key == enum.FacilityId.Facility_Id.value:
                    facility_id = credential.value

            request_dict = provider.meta_data.get('request_dict', {})
            mapped_request_dict = {
                "requestDict": ConfigureLot.map_with_request_dict(credentials=configurations.credentials,
                                                                  request_dict=request_dict)}

            if request_data.meta_data_list:
                mapped_request_dict.update(request_data.meta_data_list[index])
            else:
                mapped_request_dict.update(request_data.meta_data)

            if provider.auth_type == enum.AuthType.BASIC.value:
                basic_auth_token = AuthService.generate_basic_auth_token(create_creds.client_id,
                                                                         create_creds.client_secret)
                create_creds.access_token = basic_auth_token

            create_creds.meta_data = mapped_request_dict
            create_creds.client_secret = encrypt_value(create_creds.client_secret)

            if configurations.cred_id:
                provider_cred_instance = base.ProviderCreds.update_by_id(db, configurations.cred_id, create_creds)
            else:
                provider_cred_instance = base.ProviderCreds.create(db, create_creds)

            provider_cred_dict = provider_cred_instance.provider_cred_to_dict()

            if isinstance(configurations.parking_lot, list):

                for parking_lot in configurations.parking_lot:
                    parking_lot_obj = base.ConnectParkinglot.get_parking_lot(db, parking_lot)
                    if parking_lot_obj:
                        provider_cred_dict_copy = provider_cred_dict.copy()
                        provider_cred_dict_copy.update({"parking_lot_id": parking_lot_obj.id,
                                                        "facility_id": facility_id,
                                                        "meta_data": {"requestDict"}})

                        data.append(provider_cred_dict_copy)
            else:
                parking_lot = configurations.parking_lot
                parking_lot_obj = base.ConnectParkinglot.get_parking_lot(db, parking_lot)
                if parking_lot_obj:
                    provider_cred_dict_copy = provider_cred_dict.copy()
                    provider_cred_dict_copy.update({"parking_lot_id": parking_lot_obj.id,
                                                    "facility_id": facility_id})
                    data.append(provider_cred_dict_copy)
        return data

    @staticmethod
    def get_payment_provider_config_service(db, provider, features, org_id):
        provider_id = provider.id
        feature_id = features[0]
        features_list = []
        provider_global_data = {}

        try:
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
            parking_lots = []
            for feature_id in features:
                feature = base.Feature.get(db, feature_id)
                if not feature:
                    return api_response(
                        message="Feature doesn't exists",
                        status="error",
                        data=[],
                        status_code=404
                    )

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
                    feature_event_types = base.FeatureEventType.get_all_by_provider_connect_and_feature(db,
                                                                                                        provider_connect.id,
                                                                                                        feature.id)
                    if feature_event_types:
                        connected_provider_connects.append(provider_connect)

                grouped_by_parking_lot = defaultdict(list)
                for provider_connect in connected_provider_connects:
                    grouped_by_parking_lot[provider_connect.connect_id].append(provider_connect)

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
                                                                                                 provider_creds)
                        if provider.name.lower() == 'tiba':
                            provider_data['credentials'] = configuration_settings
                            provider_global_data = configuration_settings
                            provider_data['provider_creds'] = provider_creds_data

                        parking_lot_dict['credentials'] = configuration_settings
                        parking_lot_dict['provider_creds'] = provider_creds_data
                    else:
                        configuration_settings = ConfigureLot.get_provider_meta_data_with_values(provider,
                                                                                                 provider_creds_data,
                                                                                                 provider_creds)

                        provider_data['credentials'] = configuration_settings
                        provider_data['provider_creds'] = provider_creds_data

                        if provider.name.lower().startswith('oobeo'):
                            parking_lot_dict['credentials'] = configuration_settings
                            parking_lot_dict['provider_creds'] = provider_creds_data

                    parking_lots.append(json.loads(json.dumps(parking_lot_dict, default=custom_encoder)))

                if base.ParkinglotProviderFeature.get_by_feature_id(db, feature.id):
                    features_list.append(feature_data)
        except Exception as e:
            logger.error(f"An error occurred while fetching payment provider config details: {str(e)}")

        provider_data['credentials'] = provider_global_data

        def remove_duplicates(data):
            seen = set()
            unique_data = []
            for entry in data:
                parking_lot_id = entry.get('parking_lot_id')
                if parking_lot_id not in seen:
                    unique_data.append(entry)
                    seen.add(parking_lot_id)
            return unique_data
        parking_lots = remove_duplicates(parking_lots)

        return provider_data, features_list, parking_lots

    @staticmethod
    def cred_update_service(db, data_to_update: schema.NewConfigSettings, org):
        response, new_parking_lot = [], False

        try:
            external_detach_parking_lots=[]
            if data_to_update.detach_parking_lots:
                for dt in data_to_update.detach_parking_lots:
                    connect_parkinglot = base.ConnectParkinglot.get_connect_parking_lot_id(db, dt['parkingLotID'])
                    base.ProviderConnect.detach_parking_lot(db, dt['providerCredsID'], connect_parkinglot.id)
                    base.ProviderCreds.soft_delete_provider_cred(db, dt['providerCredsID'])
                    base.SubTask.soft_delete_sub_task(db, dt['providerCredsID'])
                    provider_details = base.ProviderConnect.get_full_provider_creds(db, connect_id=connect_parkinglot.id, provider_creds_id=dt['providerCredsID'])
                    if provider_details and provider_details["feature_type"] == enum.FeatureType.PAYMENT.value:
                        if provider_details["feature_type_key"] == enum.Feature.PAYMENT_CHECK_SPOT.value:
                            feature = "spot"
                        else:
                            feature = "lpr"
                        external_detach_parking_lots.append({
                            "parking_lot_id": provider_details["parking_lot_id"],
                            "provider": provider_details["provider_name"],
                            "feature": feature,
                            "org_id": org.org_id
                        })

            features = data_to_update.features
            external_update_cred_details = []
            for feature in features:
                feature_obj = base.Feature.get(db, feature)
                connect_feature_provider_cred = schema.ConnectFeatureProviderCred(
                    feature_id=feature or None,
                    provider_id=data_to_update.provider_id or None,
                    auth_level=data_to_update.auth_level or None,
                    config_settings=[],
                    features=features)

                for data in data_to_update.config_settings:
                    if data.cred_id:
                        cred_by_id = base.ProviderCreds.get_by_id(db, data.cred_id)

                        # Add/update provider cred for a new parking lot
                        if connect_feature_provider_cred.auth_level != enum.AuthLevel.PARKING_LOT.value:
                            if isinstance(data.parking_lot, int):
                                data_parking_lot = [data.parking_lot]
                            else:
                                data_parking_lot = data.parking_lot
                            for parking_lot in data_parking_lot:
                                is_connected = base.ProviderConnect.get_provider_connect_by_parking_lot_connect(db,
                                                                                                                parking_lot,
                                                                                                                data.cred_id)
                                if not is_connected:
                                    new_parking_lot = True

                                    if len(connect_feature_provider_cred.config_settings) == 0:
                                        connect_feature_provider_cred.config_settings.append(schema.ConfigSettingsGlobal(
                                            parking_lot=[parking_lot],
                                            cred_id=data.cred_id,
                                            credentials=data.credentials,
                                            meta_data=data.meta_data))
                                    else:
                                        connect_feature_provider_cred.config_settings[0].id.append(parking_lot)

                        if not cred_by_id:
                            response.append({
                                "message": f" credential not found with ID {data.cred_id}. Skipping.",
                                "status": "skipped"
                            })
                            continue

                        update_cred = schema.UpdateCred()
                        for credential in data.credentials:
                            if hasattr(update_cred, credential.key):
                                setattr(update_cred, credential.key, credential.value)
                        provider = base.Provider.get_by_id(db, data_to_update.provider_id)
                        request_dict = {}

                        if provider:
                            request_dict = provider.meta_data.get('request_dict', {})
                        mapped_request_dict = {
                            "requestDict": ConfigureLot.map_with_request_dict(credentials=data.credentials,
                                                                            request_dict=request_dict)}
                        update_cred.client_secret = encrypt_value(update_cred.client_secret)

                        if data.meta_data:
                            update_cred.meta_data = data.meta_data
                        else:
                            update_cred.meta_data = mapped_request_dict

                        if data.credentials:
                            meta_dict = {}
                            for creden in data.credentials:
                                meta_dict[creden.key] = creden.value
                            update_cred.meta_data.update(meta_dict)

                            if meta_dict and meta_dict.get('facility_id'):
                                connect_parkinglot = base.ConnectParkinglot.get_connect_parking_lot_id(db, data.parking_lot)
                                provider_connect = base.ProviderConnect.get_provider_connect(db, connect_parkinglot.id,
                                                                                            data.cred_id)
                                base.ProviderConnect.update_facility_id(db, provider_connect.id, meta_dict.get('facility_id'))

                        if feature_obj.feature_type == enum.FeatureType.PAYMENT:
                            if feature_obj.text_key == enum.Feature.PAYMENT_CHECK_SPOT.value:
                                feature = "spot"
                            else:
                                feature = "lpr"
                            meta_data = update_cred.meta_data or {}
                            mapped_cred = {
                                "org_id": org.org_id,
                                "parking_lot_id": data.parking_lot,
                                "client_id": update_cred.client_id,
                                "client_secret": update_cred.client_secret,
                                "provider": provider.text_key,
                                "feature": feature,
                                "api_key": update_cred.api_key,
                                "facility_id": str(meta_data["facility_id"]) if meta_data.get("facility_id") else None,
                                "meta_data": meta_data,
                                "tags": meta_data.get("tags"),
                            }
                            external_update_cred_details.append(mapped_cred)

                        # update creds in SGConnect
                        base.ProviderCreds.update_by_id(db, cred_by_id.id, update_cred)

                    else:
                        # Add/update provider cred for a new parking lot
                        is_connected = base.ProviderConnect.get_provider_connect_by_parking_lot_connect(db,
                                                                                                        data.parking_lot,
                                                                                                        data.cred_id)

                        if not is_connected:
                            new_parking_lot = True
                            non_global = schema.ConfigSettingsNonGlobal(parking_lot=data.parking_lot,
                                                                        credentials=data.credentials,
                                                                        meta_data=data.meta_data)
                            connect_feature_provider_cred.config_settings.append(non_global)

                if new_parking_lot:
                    ConfigureLot.feature_provider_cred_lot_mapping_service(db, connect_feature_provider_cred, org)

            # If the feature is payment, perform the external API call

            if external_update_cred_details or external_detach_parking_lots:
                try:
                    payment_update_result = ConfigureLot.update_payment_provider_instance(
                        db,
                        external_update_cred_details,
                        external_detach_parking_lots,
                        org.org_id
                    )
                    if not payment_update_result:
                        db.rollback()
                        raise ValueError("Payment provider update failed.")
                except Exception as e:
                    db.rollback()
                    response.append({
                        "message": f"Failed to update credentials: {str(e)}",
                        "status": "error"
                    })
                    return response

        except Exception as e:
            db.rollback()
            response.append({
                "message": f"Failed to update credentials: {str(e)}",
                "status": "error"
            })
        finally:
            return response

    @staticmethod
    def detach_parking_lot(db, parking_lot_ids, provider_id):
        provider_creds = base.ProviderCreds.get_by_provider(db, provider_id)

        provider_creds_ids = []
        for provider_cred in provider_creds:
            provider_creds_ids.append(provider_cred.id)

        for parking_lot in parking_lot_ids:
            for provider_creds_id in provider_creds_ids:
                base.ProviderConnect.detach_parking_lot(db, provider_creds_id, parking_lot)
        return

    @staticmethod
    def get_connected_parking_lots(db, provider_id, feature_id, org_id):
        provider_connects = base.ProviderConnect.get_provider_connects(db, provider_id, feature_id, org_id)
        connected_provider_connects = []
        for provider_connect in provider_connects:
            feature_event_types = base.FeatureEventType.get_all_by_provider_connect_and_feature(db, provider_connect.id,
                                                                                                feature_id)
            if feature_event_types:
                connected_provider_connects.append(provider_connect)

        grouped_by_parking_lot = defaultdict(list)
        for provider_connect in connected_provider_connects:
            grouped_by_parking_lot[provider_connect.connect_id].append(provider_connect)

        parking_lots = []
        for parking_lot, grouped_provider_connect in grouped_by_parking_lot.items():
            parking_lots.append(parking_lot)

        return parking_lots

    @staticmethod
    def get_detaching_parking_lots(db, connected_parking_lots, data_to_update):
        detaching_parking_lots_list = []
        connected_parking_lots_list = []

        for parking_lot in connected_parking_lots:
            parking_lot_obj = base.ConnectParkinglot.get_by_id(db, parking_lot)
            connected_parking_lots_list.append(parking_lot_obj.parking_lot_id)

        for data in data_to_update.config_settings:
            if type(data) == list:
                for d in data:
                    detaching_parking_lots_list.append(d.parking_lot)
            else:
                detaching_parking_lots_list.append(data.parking_lot)

        list1 = detaching_parking_lots_list
        list2 = connected_parking_lots_list
        if type(list1[0]) == list:
            list1 = list1[0]

        set1 = set(list1)
        set2 = set(list2)
        unique_to_list1 = set1 - set2
        unique_to_list2 = set2 - set1

        unique_items = list(unique_to_list1.union(unique_to_list2))
        result_list = []
        for item in unique_items:
            connect_parkinglot = base.ConnectParkinglot.get(db, item)
            if connect_parkinglot:
                result_list.append(connect_parkinglot.id)
        return result_list

    @staticmethod
    def reset_attributes(instance, exclude=None):
        if exclude is None:
            exclude = []
        for attr in instance.__annotations__:
            if attr not in exclude:
                setattr(instance, attr, None)

    @staticmethod
    def map_with_request_dict(credentials: [],
                              request_dict: dict):
        # if request_dict is None:
        #     return {}
        # for credential in credentials:
        #     if credential.label in request_dict:
        #         request_dict[credential.label] = credential.value
        # return request_dict
        credential_map = {credential.key: credential.value for credential in credentials}

        for key, value in request_dict.items():
            if value in credential_map:
                request_dict[key] = credential_map[value]

        return request_dict


    @staticmethod
    def get_provider_meta_data_with_values(provider, provider_creds_data, provider_creds, provider_connect_data=None):
        global_level_config = provider.meta_data.get('global_level_config', [])
        parking_lot_level_config = provider.meta_data.get('parking_lot_level_config', [])
        customer_level_config = provider.meta_data.get('customer_level_config', [])

        configuration_settings = global_level_config + parking_lot_level_config + customer_level_config
        config_dict = {setting['key']: setting for setting in configuration_settings}

        if provider_creds.client_id:
            if 'client_id' in config_dict:
                config_dict['client_id']['value'] = provider_creds.client_id

        if provider_creds.client_secret:
            client_secret = decrypt_encrypted_value(provider_creds.client_secret)
            if 'client_secret' in config_dict:
                config_dict['client_secret']['value'] = client_secret

        if provider_creds.access_token:
            access_token = decrypt_encrypted_value(provider_creds.access_token)
            if 'access_token' in config_dict:
                config_dict['access_token']['value'] = access_token

        if provider_connect_data and provider_connect_data.facility_id:
            if 'facility_id' in config_dict:
                config_dict['facility_id']['value'] = provider_connect_data.facility_id

        if provider_creds.meta_data:
            for meta_key, meta_value in provider_creds.meta_data.items():
                if meta_key in config_dict:
                    config_dict[meta_key]['value'] = meta_value

        updated_configuration_settings = list(config_dict.values())
        return updated_configuration_settings

    @staticmethod
    def upsert_violation_configuration(organisation: base.Organization, update_connect_parkinglot_schema: schema.UpdateLot):
        if not settings.IS_VIOLATION_SERVICE_ENABLED:
            return

        if not update_connect_parkinglot_schema.updated_properties.grace_period:
            return

        configurations = []
        for lot in update_connect_parkinglot_schema.parking_lot:
            configurations.append({
                "parking_lot_id": lot,
                "org_id": organisation.org_id,
                "scope": Scope.Lot.value,
                "scope_id": lot,
                "configuration": {
                    "grace_period_in_seconds": update_connect_parkinglot_schema.updated_properties.grace_period_in_seconds
                },
                "modified_by": organisation.org_name
            })
        violation_service.bulk_upsert_violation_configs(configurations)

    @staticmethod
    def create_provider_instances_bulk(bulk_payment_creds: List[Dict[str, Any]]):
        if not bulk_payment_creds:
            logger.warning("[ConfigureLot] No bulk credentials to send to PaymentService.")
            return None
        logger.info(f"[ConfigureLot] Sending bulk credentials to PaymentService: {bulk_payment_creds}")
        return payment_service.create_provider_instances_bulk(bulk_payment_creds)



    @staticmethod
    def update_payment_provider_instance(
        db,
        external_update_cred_details: List[Dict[str, Any]],
        external_detach_parking_lots: List[Dict[str, Any]],
        org_id: int
    ):
        """Update Sync payment service."""
        try:
            payload = {
                "org_id": org_id,
                "update": external_update_cred_details,
                "detach": external_detach_parking_lots
            }

            logger.info(f"[UpdateConfigureLot] Sending update payload: {payload}")
            response = payment_service.send_cred_update_payload(payload)

            # Check if the response status is "Success"
            if not isinstance(response, dict) or response.get("status") != "Success":
                raise ValueError(f"Failed to update payment provider instances: {response}")

            return True

        except Exception as e:
            logger.error(
                f"[UpdateConfigureLot] Successfully updated payment provider instances for org {org_id}: {e}"
            )
            db.rollback()
            return None
