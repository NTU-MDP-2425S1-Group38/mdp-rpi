from typing import Tuple, List, Optional

from pydantic import BaseModel, Field

from app_types.primatives.command import Command


class Instructions:
    commands:List[Command] = []

    def add(self, commands: List[Command]) -> None:
        """
        Method to add multiple commands to the queue
        :param commands:
        :return:
        """
        self.commands.extend(commands)

    def pop(self) -> Optional[Command]:
        """
        Method to pop the next instruction
        :return: Optional[Command]
        """
        if self.commands:
            return self.commands.pop(0)

        return None
