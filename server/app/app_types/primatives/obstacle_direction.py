from enum import Enum


class ObstacleDirection(int, Enum):
    """
    Directions on where the image card is placed on the obstacle.
    """
    North = 1
    South = 2
    East = 3
    West = 4
