import logging
from collections.abc import Callable
from typing import Literal, List, Optional

from app_types.obstacle import Obstacle
from app_types.primatives.command import CommandInstruction, MoveInstruction, AlgoCommandResponse
from app_types.primatives.cv import CvResponse
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
    CV methods
    """

    def capture_and_process_image(self, callback: Callable[[CvResponse], None] = lambda x: print(x)) -> None:
        self.logger.info("Capturing image!")
        image_b64 = self.camera.capture()
        self.logger.info("Captured image as b64!")
        self.connection_manager.slave_request_cv(image_b64, callback)
        return

    def _update_obstacle_label_after_cv(self, obstacle_id: int, cv_response: CvResponse) -> None:

        if cv_response.label == ObstacleLabel.Unknown:
            self.logger.warning("Received UNKNOWN as obstacle label, exiting _update_obstacle_label_after_cv")
            return

        obstacle_index = next((i for i, obs in enumerate(self.obstacles) if obs.id == obstacle_id), None)

        if not obstacle_index:
            self.logger.warning(f"Obstacle {obstacle_id} not found in gamestate, exiting _update_obstacle_label_after_cv")
            return

        # Update label internally
        self.obstacles[obstacle_index].label = cv_response.label

        # TODO update android of updated label

    def capture_and_update_label(self, obstacle_id: int) -> None:
        self.capture_and_process_image(lambda res: self._update_obstacle_label_after_cv(obstacle_id, res))


    """
    Algo methods
    """

    def _algo_response_callback(self, response: AlgoCommandResponse) -> None:
        commands = response.commands
        self.logger.info(f"Received {len(commands)} from the server!")
        self.instruction.add(commands)
        return


    def set_obstacles(self, *obstacles: Obstacle) -> None:
        """
        Method to set the obstacles in gamestate.
        This needs to be done prior to "running" task 1.
        :param obstacles: List[Obstacle]
        :return:
        """
        self.obstacles = list(obstacles)
        self.logger.info("Requesting for commands from algo server!")
        self.connection_manager.slave_request_algo(self.obstacles, self._algo_response_callback)


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




