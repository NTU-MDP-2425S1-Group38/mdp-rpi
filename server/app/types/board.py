from typing import List
from pydantic import BaseModel, Field
from types.car import Car
from types.obstacle import Obstacle


class Board(BaseModel):
    obstacles: List[Obstacle] = Field(default=[])
    car: Car = Field(default=Car())

