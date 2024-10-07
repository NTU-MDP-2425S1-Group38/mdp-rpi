from enum import Enum
from typing import List, Union

from pydantic import BaseModel, Field, field_validator, ValidationError


class SlaveWorkRequestType(str, Enum):
    Algorithm = "ALGORITHM"
    ImageRecognition = "IMAGE_RECOGNITION"


class SlaveObstacleDirection(str, Enum):
    North = 1,
    South = 2,
    East = 3,
    West = 4


class SlaveObstacle(BaseModel):
    id: int = Field(default=0)
    x: int
    y: int
    d: SlaveObstacleDirection


class SlaveWorkRequestPayloadAlgo(BaseModel):
    obstacles: List[SlaveObstacle]


class SlaveWorkRequestPayloadImageRecognition(BaseModel):
    image: str  # Base64 encoded image (UTF-8)
    ignore_bullseye: bool = Field(default=False)


class SlaveWorkRequest(BaseModel):
    id:str = Field(default="")
    type: SlaveWorkRequestType
    payload: Union[SlaveWorkRequestPayloadAlgo, SlaveWorkRequestPayloadImageRecognition]


