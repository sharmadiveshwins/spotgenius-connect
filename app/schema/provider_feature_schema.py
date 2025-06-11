from pydantic import BaseModel


class ProviderFeatureCreateSchema(BaseModel):
    provider_id: int
    feature_id: int
