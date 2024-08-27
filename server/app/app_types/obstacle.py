from pydantic import BaseModel, Field
from app_types.primatives.obstacle_direction import ObstacleDirection
from app_types.primatives.obstacle_label import ObstacleLabel
from app_types.primatives.position import Position


class Obstacle(BaseModel):
    position: Position
    direction: ObstacleDirection
    label: ObstacleLabel
    visited: bool = Field(default=False)
