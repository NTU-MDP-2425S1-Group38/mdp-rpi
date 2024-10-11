import logging
from collections.abc import Callable
from typing import Literal, List
import time
import math


from app_types.obstacle import Obstacle

from app_types.primatives.command import (
    CommandInstruction,
    MoveInstruction,
    TurnInstruction,
    AlgoCommandResponse,
)
from app_types.primatives.cv import CvResponse
from app_types.primatives.obstacle_label import ObstacleLabel
from modules.serial.android import AndroidMessage
from modules.tasks.task_two import TaskTwoRunner
from utils.instructions import Instructions
from modules.camera.camera import Camera

from modules.web_server.connection_manager import ConnectionManager
from utils.metaclass.singleton import Singleton


class GameState(metaclass=Singleton):
    """
    Singleton class for holding onto the game state.
    """

    logger = logging.getLogger("GameState")

    camera: Camera
    connection_manager: ConnectionManager

    obstacles: List[Obstacle] = []
    instruction: Instructions = Instructions()

    def __init__(self, is_outdoors: bool = False):
        self.android = None
        self.logger.info("Initialising connection manager")
        self.connection_manager = ConnectionManager()
        self.task_two_helper = TaskTwoRunner()

        self.logger.info("Initialising STM connector")

        self.is_outdoors = is_outdoors

        # Variables Related to Task 1
        self.last_image = None
        self.STM_Stopped = False

        self.start_time = 0
        self.drive_speed = 40 if self.is_outdoors else 55
        self.drive_angle = 25

        # Variables Related to Task 2
        self.num_M = 0
        self.num_obstacle = 1
        self.is_right1 = False  # track whether first obstacle was a left or right turn
        self.is_right2 = False  # track whether second obstacle was a left or right turn
        self.done_obstacle2 = False  # track whether second arrow was seen

        self.on_arrow_callback = (
            None  # callback that takes in a single argument, boolean is_right
        )

        self.capture_dist1 = 30  # distance between first arrow and where car will stop.
        self.capture_dist2 = (
            20  # distance between second arrow and where car will stop.
        )
        self.obstacle_dist1 = None  # distance between carpark and first obstacle.
        self.obstacle_dist2 = None  # distance between carpark and second obstacle.
        self.wall_dist = None  # distance driven to face wall after second obstacle.
        self.wall_complete = False  # signal wall has been tracked.
        self.obstacle2_length_half = None  # length of obstacle.

        self.turning_r = 40  # turning radius
        self.r0 = 21  # absolute distance from center line after passing obstacle 1
        self.chassis_cm = 15  # length from axle to axle
        self.wheelbase_cm = 16.5  # length between front wheels

        # tune to balance speed with precision. kachow!
        if self.is_outdoors:
            self.theta2 = 10  # angle to face second obstacle after first arc.
            self.drive_speed = 35
            self.obstacle_speed = 45
            self.wall_track_speed = 35
            self.carpark_speed = 45
        else:
            self.theta2 = 10  # angle to face second obstacle after first arc.
            self.drive_speed = 45
            self.obstacle_speed = 50
            self.wall_track_speed = 45
            self.carpark_speed = 30

        # left and right arrow IDs
        self.LEFT_ARROW_ID = "39"
        self.RIGHT_ARROW_ID = "38"

    """
    CV methods
    """

    def capture_and_process_image(
        self, callback: Callable[[CvResponse], None] = lambda x: print(x)
    ) -> None:
        self.logger.info("Capturing image!")
        image_b64 = Camera().capture()
        self.logger.info("Captured image as b64!")
        self.connection_manager.slave_request_cv(image_b64, callback)
        return

    def _update_obstacle_label_after_cv(
        self, obstacle_id: int, cv_response: CvResponse
    ) -> None:
        if cv_response.label == ObstacleLabel.Unknown:
            self.logger.warning(
                "Received UNKNOWN as obstacle label, exiting _update_obstacle_label_after_cv"
            )
            return

        obstacle_index = next(
            (i for i, obs in enumerate(self.obstacles) if obs.id == obstacle_id), None
        )

        if not obstacle_index:
            self.logger.warning(
                f"Obstacle {obstacle_id} not found in gamestate, exiting _update_obstacle_label_after_cv"
            )
            return

        # Update label internally
        self.obstacles[obstacle_index].label = cv_response.label

        # DONE update android of updated label
        self.android.send(
            AndroidMessage("TARGET", f"{obstacle_index},{cv_response.label.value}")
        )

    def capture_and_update_label(self, obstacle_id: int) -> None:
        self.capture_and_process_image(
            lambda res: self._update_obstacle_label_after_cv(obstacle_id, res)
        )

    """
    Algo methods
    """

    def _algo_response_callback(self, response: AlgoCommandResponse) -> None:
        commands = response.commands
        self.logger.info(f"Received {len(commands)} from the server!")
        self.instruction.add(commands)
        return

    def set_obstacles(self, *obstacles: Obstacle) -> Instructions:
        """
        Method to set the obstacles in gamestate.
        This needs to be done prior to "running" task 1.
        :param obstacles: List[Obstacle]
        :return:
        """
        self.obstacles = list(obstacles)
        self.logger.info("Requesting for commands from algo server!")
        self.connection_manager.slave_request_algo(
            self.obstacles, self._algo_response_callback
        )
        return self.instruction

    """
    Methods related to task 2.
    """

    def _run_task_two(self) -> None:
        self.task_two_helper.run()


    """
    Main entry methods
    """

    def run(self, task: Literal[1, 2]) -> None:
        """
        Method to start execution.
        :param task: Literal[1, 2] corresponding to which task
        :return: None
        """

        if task == 1:
            self.logger.error("Task one does not exist here!")
        elif task == 2:
            self._run_task_two()
