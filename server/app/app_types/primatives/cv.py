from typing import Optional

from pydantic import BaseModel

from app_types.primatives.obstacle_label import ObstacleLabel


class CvResponse(BaseModel):
    id: str
    label: Optional[ObstacleLabel]
