from pydantic import BaseModel, Field
from app_types.primatives.position import Position


class Car(BaseModel):
    position: Position = Field(default=Position(x=0, y=0))
    direction: float = Field(default=0.0)


