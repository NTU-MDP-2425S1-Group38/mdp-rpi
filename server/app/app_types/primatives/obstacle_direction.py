from enum import Enum


class ObstacleDirection(str, Enum):
    """
    Directions on where the image card is placed on the obstacle.
    """
    North = "NORTH"
    South = "SOUTH"
    East = "EAST"
    West = "WEST"
