from typing import List
from sqlalchemy import Column, String, Integer, ForeignKey, func, select, or_

from sqlalchemy import Column, String, Integer, ForeignKey, func, delete
from sqlalchemy.orm import Session, aliased
from app.models.base import Base
from app import schema
from app.models import base
from app.utils import enum
from app.config import settings


class ProviderConnect(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    facility_id = Column(String, nullable=False)

    connect_id = Column(Integer, ForeignKey("connect_parkinglot.id"), name="fk_connect_parkinglot_id",
                        nullable=False)

    provider_creds_id = Column(Integer, ForeignKey("provider_creds.id"), name="fk_provider_creds_id",
                               nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'provider_creds': self.provider_creds_id,
            'connect_id': self.connect_id,
            'facility_id': self.facility_id
        }

    @classmethod
    def create(cls, db: Session, create_provider_connect_schema: schema.CreateProviderConnectSchema):
        provider_connect = cls(**create_provider_connect_schema.model_dump())
        db.add(provider_connect)
        db.commit()
        db.refresh(provider_connect)
        return provider_connect

    @staticmethod
    def insert(db, connect_id, provider_creds_id, facility_id):

        p_connect = ProviderConnect(connect_id=connect_id,
                        facility_id=facility_id,
                        provider_creds_id=provider_creds_id
                        )

        db.add(p_connect)
        db.flush()
        return p_connect

    @classmethod
    def get_by_id(cls, db, connect_id: int):
        get_connect = db.query(cls).get(connect_id)
        if get_connect:
            return get_connect

    @classmethod
    def get_by_cred_id(cls, db, provider_creds_id: int):
        return db.query(cls).filter(
                cls.provider_creds_id == provider_creds_id
            ).first()

    @classmethod
    def get_feature_event_type(cls, db: Session, lot_id: int):
        feature_even_obj = db.query(cls).get(cls.feature_event_type_ids == lot_id)
        return feature_even_obj

    @classmethod
    def get_provider_connect(cls, db: Session, connect_id: int, provider_creds_id: int):
        provider_connect = (
            db.query(cls).filter(cls.connect_id == connect_id, cls.provider_creds_id == provider_creds_id)
            .first())
        return provider_connect

    @classmethod
    def check_parking_lot_with_provider(cls, db: Session, connect_id: int):
        connect_obj_list = db.query(cls).filter(cls.connect_id == connect_id).all()
        return connect_obj_list

    @classmethod
    def create(cls, db: Session, schema: schema.EnforcementProvider.ConnectWithProviderSchema):

        provider_connect_obj = ProviderConnect(**schema.model_dump())
        db.add(provider_connect_obj)
        db.commit()
        db.refresh(provider_connect_obj)
        return provider_connect_obj

    @classmethod
    def find_providers_by_event_type_and_lot(cls, db: Session, event, parking_lot_id):

        parkinglot_provider_feature = aliased(base.ParkinglotProviderFeature)
        event_types_alias = aliased(base.EventTypes)
        feature_event_type_alias = aliased(base.FeatureEventType)
        feature_alias = aliased(base.Feature)

        query = (
            db.query(cls.id)
            .join(parkinglot_provider_feature, cls.id == parkinglot_provider_feature.provider_connect_id)
            .join(feature_alias, parkinglot_provider_feature.feature_id == feature_alias.id)
            .join(feature_event_type_alias,
                  parkinglot_provider_feature.id == feature_event_type_alias.parkinglot_provider_feature_id)
            .join(event_types_alias,
                  feature_event_type_alias.event_type_id == event_types_alias.id)  # Added join with event_types_alias
            .filter(event_types_alias.text_key == event.event_key)
            .filter(cls.connect_id == parking_lot_id)
        )

        query = query.add_columns(
            feature_event_type_alias.parkinglot_provider_feature_id,
            feature_event_type_alias.feature_url_path_id,
            cls.provider_creds_id,
            feature_alias.text_key
        )

        query = query.distinct()

        results = query.all()

        grouped_results = {}
        for result in results:
            key = result[4]
            if key not in grouped_results:
                grouped_results[key] = []
            grouped_results[key].append({
                'provider_connect': result[0],
                'feature_id': result[1],
                'feature_url_path_id': result[2],
                'provider_creds_id': result[3],  # initially it was provider_id
                'text_key': result[4],
            })

        return grouped_results

    @classmethod
    def get_provider_feature(cls, db: Session, parking_lot_id: int) -> List[schema.ProviderFeatureSchema]:
        feature_url_alias = aliased(base.FeatureUrlPath)
        provider_feature_alias = aliased(base.Feature)
        provider_alias = aliased(base.Provider)
        query = ((db.query(cls.id,
                           provider_alias.name.label('provider_name'),
                           provider_feature_alias.name.label('feature_type'),
                           provider_feature_alias.description.label('description'),
                           feature_url_alias.id.label('url_path_id'))
                  .join(feature_url_alias, cls.provider_id == feature_url_alias.provider_id)
                  .join(provider_alias, cls.provider_id == provider_alias.id)
                  .join(provider_feature_alias, feature_url_alias.feature_id == provider_feature_alias.id))
                 .filter(cls.connect_id == parking_lot_id)).all()

        mapped_result = [
            schema.ProviderFeatureSchema(
                provider=item.provider_name,
                description=item.description,
                feature_type=item.feature_type,
                url_path_id=item.url_path_id
            )
            for item in query
        ]

        return mapped_result

    @classmethod
    def connect_provider_creds_with_lot(cls, db: Session, provider_creds: int, connect_parkinglot_id: int,
                                        facility_id: int):
        provider_connect_obj = ProviderConnect(provider_creds_id=provider_creds,
                                               connect_id=connect_parkinglot_id,
                                               facility_id=facility_id)
        db.add(provider_connect_obj)
        db.flush()
        # db.commit()
        # db.refresh(provider_connect_obj)
        return provider_connect_obj


    @classmethod
    def get_full_provider_creds(cls, db: Session, connect_id: int, provider_creds_id: int):
        result = (
                db.query(
                    base.ProviderCreds.client_id,
                    base.ProviderCreds.client_secret,
                    base.ProviderCreds.api_key,
                    base.ProviderCreds.meta_data,
                    base.ConnectParkinglot.parking_lot_id,
                    base.ProviderConnect.facility_id,
                    base.ProviderCreds.provider_id,
                    base.Provider.text_key.label("provider_name"),
                    base.Feature.text_key
                )
                .join(base.ConnectParkinglot, base.ConnectParkinglot.id == base.ProviderConnect.connect_id)
                .join(base.ProviderCreds, base.ProviderCreds.id == base.ProviderConnect.provider_creds_id)
                .join(base.Provider, base.Provider.id == base.ProviderCreds.provider_id)
                .join(base.ProviderFeature, base.ProviderFeature.provider_id == base.Provider.id)
                .join(base.Feature, base.Feature.id == base.ProviderFeature.feature_id)
                .filter(base.ProviderConnect.connect_id == connect_id)
                .filter(base.ProviderConnect.provider_creds_id == provider_creds_id)
                .first()
        )
        if result:
            return {
                "client_id": result.client_id,
                "client_secret": result.client_secret,
                "api_key": result.api_key,
                "meta_data": result.meta_data,
                "parking_lot_id": result.parking_lot_id,
                "facility_id": result.facility_id,
                "provider_name": result.provider_name,
                "feature_type_key": result.text_key,
                "tags": result.meta_data.get("tags", ["SG"])
            }
        return None

    @classmethod
    def detach_parking_lot(cls, db: Session, provider_cred_id: int, connect_id: int):
        provider_connects = db.query(cls).filter(cls.provider_creds_id == provider_cred_id,
                                                 cls.connect_id == connect_id
                                                 ).all()

        if not provider_connects:
            return None

        provider_connect_ids = [pc.id for pc in provider_connects]

        parking_lot_features = db.query(base.ParkinglotProviderFeature).filter(
            base.ParkinglotProviderFeature.provider_connect_id.in_(provider_connect_ids)
        ).all()

        lot_feature_ids = [f.id for f in parking_lot_features]

        if lot_feature_ids:
            db.query(base.FeatureEventType).filter(
                base.FeatureEventType.parkinglot_provider_feature_id.in_(lot_feature_ids)
            ).delete(synchronize_session=False)

            db.query(base.ParkinglotProviderFeature).filter(
                base.ParkinglotProviderFeature.id.in_(lot_feature_ids)
            ).delete(synchronize_session=False)

        db.query(cls).filter(
            cls.id.in_(provider_connect_ids)
        ).delete(synchronize_session=False)

        db.commit()
        return 'Deleted successfully'

    @classmethod
    def get_connected_provider(cls, db: Session, filter_by: str, parking_lot_ids: List[int], org: base.Organization, can_view: bool):

        system_type = {
            'provider.enforcement': 'Enforcement System',
            'provider.payment': 'Payment System',
            'provider.reservation': 'Reservation System'
        }

        results = (
            db.query(
                ProviderConnect.provider_creds_id,
                base.ProviderCreds.provider_id,
                base.Feature.text_key,
                func.count(func.distinct(ProviderConnect.connect_id, ProviderConnect.provider_creds_id)).label('connected_provider_count'),

            )
            .join(base.ProviderCreds, ProviderConnect.provider_creds_id == base.ProviderCreds.id)
            .join(base.Provider, base.ProviderCreds.provider_id == base.Provider.id)
            .join(base.ProviderTypes, base.Provider.provider_type_id == base.ProviderTypes.id)
            .join(base.ParkinglotProviderFeature,
                  ProviderConnect.id == base.ParkinglotProviderFeature.provider_connect_id)
            .join(base.Feature,  base.Feature.id == base.ParkinglotProviderFeature.feature_id)
            .join(base.FeatureEventType, base.ParkinglotProviderFeature.id == base.FeatureEventType.parkinglot_provider_feature_id)
            .filter(ProviderConnect.connect_id.in_(parking_lot_ids))
            .filter(or_(can_view, base.Provider.text_key != "SpotgeniusDemo"))
            .filter(base.ProviderTypes.text_key == filter_by)
            .filter(base.Feature.feature_type != "UNDEFINED")
            .group_by(
                  ProviderConnect.provider_creds_id,
                  base.ProviderCreds.provider_id,
                  base.Feature.text_key,
                  base.Provider.id
                  ).all()
        )
        provider_details_dict = {}

        if results:

            for provider_creds_id, provider_id, text_key, connected_provider_count in results:
                feature_id = db.query(base.Feature.id).filter(base.Feature.text_key == text_key).all()

                if (provider_id, text_key) not in provider_details_dict:
                    provider = db.query(base.Provider).filter_by(id=provider_id).first()
                    provider_type = db.query(base.ProviderTypes).filter_by(id=provider.provider_type_id).first()
                    split_provider_name = settings.PROVIDER_CARDS_NAME.split(",")
                    service_type = (
                        provider.name
                        if provider.name in split_provider_name
                        else provider.name + " " + system_type[provider_type.text_key]
                    )
                    provider_details_dict[(provider_id, text_key)] = {
                        'id': provider_id,
                        'name': provider.name,
                        'logo_url': provider.logo,
                        'text_key': provider.text_key,
                        'auth_type': (
                                'basic' if provider.auth_type == 'basicbase64' else
                                'Login' if provider.auth_type == 'jcookie' else
                                provider.auth_type
                            ),
                        'feature_id': [id[0] for id in feature_id],
                        'service_type': service_type,
                        'count_parking_lots': connected_provider_count
                    }
                else:
                    provider_details_dict[(provider_id, text_key)]['count_parking_lots'] += connected_provider_count

        provider_details = [
            schema.ConnectedProvider(
                id=details['id'],
                name=details['name'],
                text_key=details['text_key'],
                logo_url=details['logo_url'],
                auth_type=details['auth_type'],
                feature_id=details['feature_id'],
                service_type=details['service_type'],
                count_parking_lots=details['count_parking_lots']
            ) for details in provider_details_dict.values()
        ]

        parking_lot = db.query(base.ConnectParkinglot).filter_by(id=parking_lot_ids[0]).first()
        if parking_lot:
            pricing_type = enum.PricingType.FIXED.value
            violation_conf = base.ViolationConfiguration.get_violation_by_lot_id(db, parking_lot.id)
            if violation_conf:
                pricing_type = violation_conf.pricing_type
            contact_detail = schema.ContactDetails(contact_name=org.contact_name if org.contact_name else
                                                   parking_lot.contact_name,
                                                   contact_email=org.contact_email if org.contact_email else
                                                    parking_lot.contact_email,
                                                   is_in_out_policy=parking_lot.is_in_out_policy,
                                                   grace_period=parking_lot.grace_period,
                                                   retry_number=parking_lot.retry_mechanism,
                                                   pricing_type=pricing_type
                                                   )
        else:
            contact_detail = schema.ContactDetails(contact_name=org.contact_name,
                                                   contact_email=org.contact_email)

        return schema.ProviderDetails(contact_details=contact_detail,
                                      connected_provider=provider_details)

    @classmethod
    def get_provider_connects(cls, db: Session, provider_id: int, feature_id: int, org_id: int):
        subquery_organization = select(base.Organization.id).where(base.Organization.org_id == org_id).scalar_subquery()
        subquery_parkinglot = select(base.ConnectParkinglot.id).where(
            base.ConnectParkinglot.organization_id == subquery_organization).scalar_subquery()
        subquery_provider_creds = select(base.ProviderCreds.id).where(
            base.ProviderCreds.provider_id == provider_id).scalar_subquery()

        provider_connects = db.query(ProviderConnect).filter(
            ProviderConnect.connect_id.in_(subquery_parkinglot),
            ProviderConnect.provider_creds_id.in_(subquery_provider_creds)
        ).all()
        return provider_connects

    @classmethod
    def get_by_lot_id(cls, db: Session, lot_id):
        return db.query(cls).filter_by(connect_id=lot_id).first()

    @classmethod
    def is_associate(cls, db: Session, parking_lot_id: int,
                     provider_id: int,
                     feature_id: int) -> bool:

        associate_parking_lot = (db.query(cls).join(
            base.ProviderCreds, cls.provider_creds_id == base.ProviderCreds.id
        ).filter(
            cls.connect_id == parking_lot_id,
            base.ProviderCreds.provider_id == provider_id
        ).first())
        return associate_parking_lot is not None

    @classmethod
    def get_provider_with_org_and_parking_lot(cls, db: Session, org_id: int, provider_id: int):

        results = (
            db.query(base.ConnectParkinglot.parking_lot_id)
            .join(ProviderConnect, base.ConnectParkinglot.id == ProviderConnect.connect_id)
            .join(base.ParkinglotProviderFeature,
                  ProviderConnect.id == base.ParkinglotProviderFeature.provider_connect_id)
            .join(base.FeatureEventType,
                  base.ParkinglotProviderFeature.id == base.FeatureEventType.parkinglot_provider_feature_id)
            .filter(
                ProviderConnect.provider_creds_id.in_(
                    db.query(base.ProviderCreds.id).filter(base.ProviderCreds.provider_id == provider_id)
                ), base.ConnectParkinglot.organization_id == org_id).distinct().all())

        parking_lot_ids = [result.parking_lot_id for result in results]

        return parking_lot_ids

    @classmethod
    def get_provider_connect_by_parking_lot_connect(cls, db: Session, parking_lot_id: int, provider_creds_id: int):

        return db.query(cls).join(
            base.ConnectParkinglot, base.ConnectParkinglot.id == ProviderConnect.connect_id
        ).filter(
            base.ConnectParkinglot.parking_lot_id == parking_lot_id,
            ProviderConnect.provider_creds_id == provider_creds_id
        ).first()

    @classmethod
    def delete_provider_connect_by_parking_lot_and_provider_creds_ids(cls, db: Session, parking_lot_ids: list,
                                                                      provider_creds_ids: list):
        stmt = delete(ProviderConnect).where(
            ProviderConnect.connect_id.in_(parking_lot_ids) &
            ProviderConnect.provider_creds_id.in_(provider_creds_ids)
        )
        db.execute(stmt)
        db.commit()

    @classmethod
    def delete(cls, db: Session, provider_connect_id: int):
        db.query(cls).filter(cls.id == provider_connect_id).delete()
        db.commit()

    @classmethod
    def update_facility_id(cls, db: Session, provider_connect_id: int, facility_id: int):
        db.query(cls).filter(cls.id == provider_connect_id).update({cls.facility_id: facility_id})


    @classmethod
    def check_enforcement_provider_connected(cls, db: Session, parking_lot_id):
        query = (
            db.query(base.Provider)
            .join(base.ProviderCreds, base.Provider.id == base.ProviderCreds.provider_id)
            .join(cls, base.ProviderCreds.id == cls.provider_creds_id)
            .join(base.ProviderTypes, base.Provider.provider_type_id == base.ProviderTypes.id)
            .filter(
                ProviderConnect.connect_id == parking_lot_id,
                base.ProviderTypes.text_key == "provider.enforcement",
            )
            .all()
        )
        return query

    @classmethod
    def is_only_paris_connected(cls, db: Session, parking_lot_id, provider_text_key: str,
                                provider_type_text_key: str):

        query = (
            db.query(base.Provider)
            .join(base.ProviderCreds, base.Provider.id == base.ProviderCreds.provider_id)
            .join(cls, base.ProviderCreds.id == cls.provider_creds_id)
            .join(base.ProviderTypes, base.Provider.provider_type_id == base.ProviderTypes.id)
            .filter(
                ProviderConnect.connect_id == parking_lot_id,
                base.ProviderTypes.text_key == provider_type_text_key,
            )
            .all()
        )


        # Validate the list length and provider_text_key match
        if len(query) == 1:
            # Assuming you can access text_key like this; adjust if needed
            return query[0].text_key == provider_text_key

        return False


