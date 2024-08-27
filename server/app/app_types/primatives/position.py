from pydantic import BaseModel


class Position(BaseModel):
    """
    Represents a position on the board, typically within [0, 19]
    """
    x: int
    y: int
