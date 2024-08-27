from typing import List
from pydantic import BaseModel, Field
from app_types.car import Car
from app_types.obstacle import Obstacle


class Board(BaseModel):
    obstacles: List[Obstacle] = Field(default=[])
    car: Car = Field(default=Car())

