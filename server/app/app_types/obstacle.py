from typing import Optional
from pydantic import BaseModel, Field, model_serializer
from app_types.primatives.obstacle_direction import ObstacleDirection
from app_types.primatives.obstacle_label import ObstacleLabel
from app_types.primatives.position import Position


class Obstacle(BaseModel):
    id: int
    position: Position
    direction: ObstacleDirection
    label: ObstacleLabel = Field(default=ObstacleLabel.Unknown)
    visited: bool = Field(default=False)

    @model_serializer()
    def _serial(self):
        return {
            "id": self.id,
            "x": self.position.x,
            "y": self.position.y,
            "d": self.direction,
        }
