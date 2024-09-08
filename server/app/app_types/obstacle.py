from pydantic import BaseModel, Field, model_serializer
from app_types.primatives.obstacle_direction import ObstacleDirection
from app_types.primatives.obstacle_label import ObstacleLabel
from app_types.primatives.position import Position


class Obstacle(BaseModel):
    position: Position
    direction: ObstacleDirection
    label: ObstacleLabel
    visited: bool = Field(default=False)

    @model_serializer()
    def _serial(self):
        return {
            "x": self.position.x,
            "y": self.position.y,
            "d": self.direction
        }
