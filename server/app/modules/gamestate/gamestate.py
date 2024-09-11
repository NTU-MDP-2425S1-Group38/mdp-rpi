import logging
from typing import Literal, List, Optional

from app_types.obstacle import Obstacle
from app_types.primatives.command import CommandInstruction, MoveInstruction
from app_types.primatives.obstacle_label import ObstacleLabel
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

        # self.logger.info("Initialising STM connector")
        # self.stm = STM()


    """
    Helper methods
    """

    def capture_and_process_image(self) -> Optional[ObstacleLabel]:
        self.logger.info("Capturing image!")
        # image_b64 = self.camera.capture()
        # self.logger.info("Captured image as b64!")
        # label = self.connection_manager.slave_request_cv(image_b64)
        # self.logger.info(f"Image labeled as: {label}")
        # return label
        return None


    """
    Public method to update gamestate
    """

    def set_obstacles(self, *obstacles: Obstacle) -> None:
        """
        Method to set the obstacles in gamestate.
        This needs to be done prior to "running" task 1.
        :param obstacles: List[Obstacle]
        :return:
        """
        self.obstacles = list(obstacles)
        self.logger.info("Requesting for commands from algo server!")

        commands = self.connection_manager.slave_request_algo(self.obstacles)
        self.logger.info(f"Received {len(commands)} from the server!")
        self.instruction.add(commands)

    """
    Methods related to task 1.
    """

    def _run_task_one(self) -> None:
        """
        Method to run task one.
        Obstacles need to be set and instructions need to be added prior to running.
        :return: None
        """
        self.logger.info("Starting task one running loop!")
        while cmd := self.instruction.pop():

            self.logger.info(f"Current command: {cmd.model_dump()}")

            if isinstance(cmd.value, CommandInstruction):
                pass

            if isinstance(cmd.value, MoveInstruction):
                pass

        self.logger.info("Run Task One completed!")


    """
    Main entry methods
    """

    def run(self, task: Literal[1, 2]) -> None:
        """
        Method to start execution.
        :param task: Literal[1, 2] corresponding to which task
        :return: None
        """
        if task==1:
            self._run_task_one()




