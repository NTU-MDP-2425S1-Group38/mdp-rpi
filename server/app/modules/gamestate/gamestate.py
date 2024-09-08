import logging
from typing import Literal, List

from app_types.obstacle import Obstacle
from app_types.primatives.command import CommandInstruction, MoveInstruction
from utils.instructions import Instructions
from modules.camera.camera import Camera
from modules.serial.stm32 import STM
from modules.web_server.connection_manager import ConnectionManager
from utils.metaclass.singleton import Singleton


class GameState(metaclass=Singleton):
    """
    Singleton class for holding onto the game state.
    """

    logger = logging.getLogger("GameState")

    camera:Camera
    connection_manager:ConnectionManager
    stm:STM

    obstacles: List[Obstacle] = []
    instruction: Instructions = Instructions()


    def __init__(self):
        self.logger.info("Initialising camera")
        self.camera = Camera()

        self.logger.info("Initialising connection manager")
        self.connection_manager = ConnectionManager()

        self.logger.info("Initialising STM connector")
        self.stm = STM()

    def set_obstacles(self, *obstacles: Obstacle) -> None:
        self.obstacles = list(obstacles)
        self.logger.info("Requesting for commands from algo server!")

        commands = self.connection_manager.slave_request_algo(self.obstacles)
        self.logger.info(f"Received {len(commands)} from the server!")
        self.instruction.add(commands)

    def _run_task_one(self) -> None:
        self.logger.info("Starting task one running loop!")
        while cmd := self.instruction.pop():

            self.logger.info(f"Current command: {cmd.model_dump()}")

            if isinstance(cmd.value, CommandInstruction):
                pass

            if isinstance(cmd.value, MoveInstruction):
                pass

        self.logger.info("Run Task One completed!")


    def run(self, task: Literal[1, 2]) -> None:
        """
        Method to start execution.
        :param task: Literal[1, 2] corresponding to which task
        :return: None
        """
        if task==1:
            self._run_task_one()




