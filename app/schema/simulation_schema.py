from pydantic import BaseModel
from typing import List

class SimulationCreateSchema(BaseModel):
    input_data: List[dict]