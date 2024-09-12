from enum import Enum
from typing import Union, List, Optional

from pydantic import BaseModel, Field, field_validator, ValidationError


class Direction(int, Enum):
    North = 1,
    South = 2,
    East = 3,
    West = 4


# Enum for movement directions
class MoveDirection(str, Enum):
    Forward = "FORWARD"
    ForwardRight = "FORWARD_RIGHT"
    ForwardLeft = "FORWARD_LEFT"
    Backward = "BACKWARD"
    BackwardRight = "BACKWARD_RIGHT"
    BackwardLeft = "BACKWARD_LEFT"


# Model for move instructions with an amount (for moves like FORWARD, BACKWARD)
class MoveInstruction(BaseModel):
    move: MoveDirection
    amount: float = Field(default=0.0)


class CommandInstruction(str, Enum):
    Finish = "FIN"
    Capture = "CAPTURE_IMAGE"


class EndPosition(BaseModel):
    x: int
    y: int
    d: Direction


class Command(BaseModel):
    cat:str = Field(default="control")
    end_position: EndPosition
    value: Union[CommandInstruction, MoveInstruction, MoveDirection]
    capture_id: Optional[int]  # ONLY FOR CAPTURE IMAGE INSTRUCTION

    @classmethod
    @field_validator('value', mode='before')
    def validate_value(cls, v):
        if isinstance(v, str):
            # Ensure it's a valid CommandInstruction
            if v in CommandInstruction.__members__.values():
                return CommandInstruction(v)
            else:
                raise ValueError(f"Invalid command instruction: {v}")
        elif isinstance(v, dict):
            # If it's a dict, assume it's a MoveInstruction
            return MoveInstruction(**v)
        else:
            raise ValueError(f"Invalid value type: {type(v)}")




class AlgoCommandResponse(BaseModel):
    id:str
    commands: List[Command]
