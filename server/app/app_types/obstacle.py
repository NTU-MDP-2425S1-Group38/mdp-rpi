from typing import Optional
from pydantic import BaseModel, Field, model_serializer, model_validator
from app_types.primatives.obstacle_direction import ObstacleDirection
from app_types.primatives.obstacle_label import ObstacleLabel
from app_types.primatives.position import Position


class Obstacle(BaseModel):
    id: int
    position: Position
    direction: ObstacleDirection
    label: ObstacleLabel = Field(default=ObstacleLabel.Unknown)
    visited: bool = Field(default=False)

    # Dynamically generate the 'id' during instantiation
    @classmethod
    @model_validator(mode="before")
    def generate_id(cls, values):
        position = values.get("position")
        direction = values.get("direction")
        if (position and direction is not None) and values.get["id"] is not None:
            values["id"] = 10_000 * position.x + 100 * position.y + direction
        return values

    @model_serializer()
    def _serial(self):
        return {
            "id": self.id,
            "x": self.position.x,
            "y": self.position.y,
            "d": self.direction,
        }
