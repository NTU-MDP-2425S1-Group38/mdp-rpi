from pydantic import BaseModel, Field


class Instruction:
    commands = Field(default=[])
