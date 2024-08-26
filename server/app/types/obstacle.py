from pydantic import BaseModel, Field
from types.primatives.obstacle_direction import ObstacleDirection
from types.primatives.obstacle_label import ObstacleLabel
from types.primatives.position import Position


class Obstacle(BaseModel):
    position: Position
    direction: ObstacleDirection
    label: ObstacleLabel
    visited: bool = Field(default=False)
