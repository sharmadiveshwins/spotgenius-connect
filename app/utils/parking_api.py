from fastapi.encoders import jsonable_encoder

from app import schema
from app.config import settings
from app.models import base
from app.service.violation_rest_service import violation_service
from app.utils import enum
from app.schema import CreateOrganizationSchema, CreateParkinglotSchema, ParkingTimeSchema, CreateFeatureEventType
from app.utils.common import convert_time_to_utc_by_timezone, convert_max_park_time_to_minutes
from app.models.base import ParkingTime
from app.utils.enum import Scope, ViolationType, ParkingOperations


class ParkingAPI:

    @staticmethod
    def ConfigureOverstayViolationEventType(db, connect_parkinglot, operation_type):
        features = base.Feature.get_all_by_text_key(
                    db,
                    (
                        enum.Feature.NOTIFY_SG_ADMIN.value,
                        enum.Feature.ENFORCEMENT_CITATION.value,
                    )
                )

        for feature in features:
            event_type = base.EventTypes.get_by_text(db, enum.EventTypes.OVERSTAY_VIOLATION.value).first()

            # provider = base.Provider.get_provider_by_provider_type(db, enum.ProviderTypes.PROVIDER_VIOLATION.value)
            # feature_url_path = base.FeatureUrlPath.get_feature_by_provider_id(db, provider.id)
            provider_connects = db.query(base.ProviderConnect).filter(base.ProviderConnect.connect_id == connect_parkinglot.id).all()

            new_feature_event_type = None
            if provider_connects and feature:
                for provider_connect in provider_connects:
                    provider_cred = db.query(base.ProviderCreds).filter(
                        base.ProviderCreds.id == provider_connect.provider_creds_id
                    ).first()

                    provider_feature = db.query(base.ProviderFeature).filter(
                        base.ProviderFeature.feature_id == feature.id,
                        base.ProviderFeature.provider_id == provider_cred.provider_id
                    ).first()

                    if provider_feature:
                        feature_url_path = base.FeatureUrlPath.get_by_provider_feature_id(db, provider_feature_id=provider_feature.id)

                        parkinglot_provider_features = db.query(base.ParkinglotProviderFeature).filter(
                            base.ParkinglotProviderFeature.provider_connect_id == provider_connect.id,
                            base.ParkinglotProviderFeature.feature_id == feature.id).all()
                        
                        for parkinglot_provider_feature in parkinglot_provider_features:
                            feature_event_type = db.query(base.FeatureEventType).filter(
                                base.FeatureEventType.event_type_id == event_type.id,
                                base.FeatureEventType.parkinglot_provider_feature_id == parkinglot_provider_feature.id).first()

                            # if feature_event_type and operation_type == enum.PaymentWindowOperationType.always_paid_parking.value:
                            if feature_event_type and (operation_type == enum.ParkingOperations.paid_24_hours.value or operation_type == enum.ParkingOperations.spot_based_24_hours_free_parking.value):
                                base.FeatureEventType.delete(db, feature_event_type.id)
                            
                            # if not feature_event_type and operation_type != enum.PaymentWindowOperationType.always_paid_parking.value:
                            if not feature_event_type and operation_type != enum.ParkingOperations.paid_24_hours.value and operation_type != enum.ParkingOperations.spot_based_24_hours_free_parking.value:
                                feature_event_type_schema = CreateFeatureEventType(
                                    event_type_id=event_type.id,
                                    feature_url_path_id=feature_url_path.id,
                                    parkinglot_provider_feature_id=parkinglot_provider_feature.id,
                                    provider_id=provider_cred.provider_id
                                )
                                new_feature_event_type = base.FeatureEventType.create_feature_event_type(db,
                                                                                                        feature_event_type_schema)
                                if new_feature_event_type:
                                    break

                    if new_feature_event_type:
                        break

        return

    @staticmethod
    def create_or_update_parkinglot(db, parking_lot_id, organization_id, parking_timing_schema):
        connect_parkinglot = base.ConnectParkinglot.get(db, parking_lot_id)
        org_lot_having_grace_period = base.ConnectParkinglot.lot_by_org_filter_by_grace_period_contact_info(db, organization_id)
        if org_lot_having_grace_period:
            violation_conf = base.ViolationConfiguration.get_violation_by_lot_id(db, org_lot_having_grace_period.id)

        if not connect_parkinglot:
            connect_parkinglot_schema = CreateParkinglotSchema(
                parking_lot_id=parking_lot_id,
                organization_id=organization_id,
                parking_lot_name = parking_timing_schema.parking_lot_name,
                parking_operations=parking_timing_schema.parking_operations,
                maximum_park_time_in_minutes=convert_max_park_time_to_minutes(parking_timing_schema.max_park_time)
                if parking_timing_schema.max_park_time else None,
                grace_period= org_lot_having_grace_period.grace_period if org_lot_having_grace_period else 0,
                contact_email= org_lot_having_grace_period.contact_email if org_lot_having_grace_period else None,
                contact_name= org_lot_having_grace_period.contact_name if org_lot_having_grace_period else None,
                retry_mechanism= org_lot_having_grace_period.retry_mechanism if org_lot_having_grace_period else None,
                is_in_out_policy= org_lot_having_grace_period.is_in_out_policy if org_lot_having_grace_period else None
            )
            connect_parkinglot = base.ConnectParkinglot.create(db, connect_parkinglot_schema)

            # save violation configuration
            if org_lot_having_grace_period:
                violation_conf = base.ViolationConfiguration.get_violation_by_lot_id(db, org_lot_having_grace_period.id)

                if violation_conf and connect_parkinglot:
                    violation_configuration_schema = schema.ViolationConfigurationSchema(
                        duration= violation_conf.duration,
                        duration_amount= violation_conf.duration_amount,
                        pricing_type= violation_conf.pricing_type,
                        parking_lot_id= connect_parkinglot.id
                    )

                    base.ViolationConfiguration.create(
                        db,
                        violation_configuration_schema= violation_configuration_schema
                    )
                

        else:
            # update parking lot and operations
            connect_parkinglot.parking_lot_name = parking_timing_schema.parking_lot_name
            connect_parkinglot.parking_operations = parking_timing_schema.parking_operations
            if parking_timing_schema.max_park_time:
                connect_parkinglot.maximum_park_time_in_minutes = convert_max_park_time_to_minutes(parking_timing_schema.max_park_time)
            db.commit()
        return connect_parkinglot

    @staticmethod
    def create_or_update_organization(db, organization_id, organization_name):
        organization= base.Organization.get_org(db, organization_id)
        if not organization:
            organization = base.Organization.create(
                                                    db, 
                                                    CreateOrganizationSchema(
                                                        org_id=organization_id,
                                                        org_name=organization_name
                                                    )
                                                )
        else:
            organization.org_name = organization_name
        
        return organization

    @staticmethod
    def update_parking_timing(db, parking_timing_schema, connect_parkinglot):
        timezone = parking_timing_schema.timezone
        exclude_delete_time_records = []

        if parking_timing_schema.parking_operations == enum.ParkingOperations.specify_lpr_based_paid_parking_time.value:
            # save and update records
            for parking_timeframe in parking_timing_schema.parking_timeframes:
                start_time = convert_time_to_utc_by_timezone(parking_timeframe.start_time, timezone, '%H:%M')
                end_time = convert_time_to_utc_by_timezone(parking_timeframe.end_time, timezone, '%H:%M')

                parking_time_schema = ParkingTimeSchema(
                    start_time=start_time,
                    end_time=end_time,
                    parking_lot_id=connect_parkinglot.id
                )

                if parking_timeframe.id:
                    exclude_delete_time_records.append(parking_timeframe.id)
                    ParkingTime.update(db, parking_timeframe.id, parking_time_schema)
                else:
                    new_parking_time = ParkingTime.create(db, parking_time_schema=parking_time_schema)
                    exclude_delete_time_records.append(new_parking_time.id)


            # delete parking time records
            if (exclude_delete_time_records):
                ParkingTime.delete(db, connect_parkinglot.id, exclude_delete_time_records)

        else:
            ParkingTime.delete(db, connect_parkinglot.id, ())

        return

    @staticmethod
    def upsert_violation_config(
            connect_parkinglot: base.ConnectParkinglot,
            organization: base.Organization,
            parking_timing_schema: schema.ParkingTimingSchema):
        if not settings.IS_VIOLATION_SERVICE_ENABLED:
            return
        ParkingAPI.upsert_config(connect_parkinglot, organization, parking_timing_schema)

    @staticmethod
    def upsert_config(connect_parkinglot, organization, parking_timing_schema):
        violation_service.update_violation_config(
            parking_lot_id=connect_parkinglot.parking_lot_id,
            org_id=organization.org_id,
            scope=Scope.Lot.value,
            scope_id=connect_parkinglot.parking_lot_id,
            configuration=ParkingAPI.get_lot_violation_config_data(parking_timing_schema),
            modified_by=organization.org_name,
        )

    @staticmethod
    def get_lot_violation_config_data(parking_timing_schema):
        config_data = {
            "parking_operation": parking_timing_schema.parking_operations
        }
        if parking_timing_schema.max_park_time_in_seconds:
            config_data["max_park_time_seconds"] = parking_timing_schema.max_park_time_in_seconds
        if parking_timing_schema.parking_timeframes:
            config_data["paid_time_windows"] = jsonable_encoder(ParkingAPI.get_utc_timeframes(parking_timing_schema))
        return config_data

    @staticmethod
    def get_utc_timeframes(parking_timing_schema):
        timezone = parking_timing_schema.timezone
        utc_timeframes = []
        for parking_timeframe in parking_timing_schema.parking_timeframes:
            start_time = convert_time_to_utc_by_timezone(parking_timeframe.start_time, timezone, '%H:%M')
            end_time = convert_time_to_utc_by_timezone(parking_timeframe.end_time, timezone, '%H:%M')
            utc_timeframes.append({"start": start_time, "end": end_time})
        return utc_timeframes


