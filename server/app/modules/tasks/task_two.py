import logging
import math
import time
from textwrap import dedent
from typing import Literal, Callable

from scipy.special.cython_special import spence

from app_types.primatives.cv import CvResponse
from app_types.primatives.obstacle_label import ObstacleLabel
from modules.camera.camera import Camera
from modules.serial import STM
from modules.serial.stm_commands import (
    StmMoveToDistance,
    StmMove,
    StmWiggle,
    StmToggleMeasure,
    StmTurn,
    StmStraight, StmSideHug, StmMoveUntilSideObstacle,
)
from modules.web_server.connection_manager import ConnectionManager
from utils.metaclass.singleton import Singleton


class TaskTwoRunner(metaclass=Singleton):
    """
    Class to run task two logic
    """

    class ConfigManeuver:
        forward_speed: int = 70
        turn_speed: int = 40

        SERVO_TURN_ANGLE = 25
        BYPASS_DISTANCE: int
        OBSTACLE_WIDTH: int

        STEP_THREE_CLOSEUP_DISTANCE: int = 30  # Distance for the robot to MOVE_FORWARD to the second obstacle
        FALLBACK_STEP_THREE_DISTANCE: int = 80

        def __init__(self):
            self.OBSTACLE_WIDTH = 0
            self.BYPASS_DISTANCE = 55

    def __init__(self):
        self.logger = logging.getLogger("TaskTwoRunner")

        self.logger.info("Instantiating Connection Manager")
        self.cm = ConnectionManager()

        self.logger.info("Instantiating STM and connecting")
        self.stm = STM()
        self.stm.connect()

        self.logger.info("Instantiating Android and connecting")
        # self.android = Android()
        # self.android.connect()

        self.config = self.ConfigManeuver()

        self.end_callback: Callable[[], None] = lambda: None

        """
        Keeps track of distance the robot has to move in a straight line before allowing to turn back in line
        with the carpark.
        """
        self.distance_to_backtrack: int = 0

    """
    HELPER METHODS
    """

    def _log_tracked_distances(self, label:str = "UNLABELED") -> None:
        self.logger.debug(dedent(f"""
            [[[\t{label.upper()}\t]]]
            BYPASS DISTANCE:\t\t{self.distance_to_backtrack}
            OFFSET DISTANCE:\t\t{self.config.OBSTACLE_WIDTH}
        """))

    def _wiggle_servo(self) -> None:
        """
        Wiggle servo to center
        :return: None
        """
        self.stm.send_stm_command_and_wait(StmWiggle())

    def _move_forward_to_distance(self, distance: int) -> None:
        """
        Move forward until the "front_distance_threshold"
        :return:
        """
        self.stm.send_stm_command_and_wait(StmMoveToDistance(distance=distance))

    def _handle_distance_result(self, payload: str) -> int:
        """
        Function to parse the returned string, calculate the proper offset
        :param payload: should be in the format of `fD{distance}`; e.g. `fD150.24`
        :return:
        """
        self.logger.info(f"Received: {payload}")
        try:
            dist_str = payload.replace("fD", "").strip()
            self.logger.debug(f"Attempting to parse this as distance: [{dist_str}]")
            return int(dist_str.split(".")[0])
        except Exception:
            self.logger.warning("Unable to parse distance! Returning 0!")
            return 0



    def _move_backwards_to_distance(self, distance: int) -> None:
        """
        Move backwards until a safe distance to maneuver.
        Assumes that the robot is already at front_distance_threshold
        :return:
        """
        self.stm.send_stm_command_and_wait(StmMoveToDistance(distance, forward=False))

    def _bypass_obstacle(self, direction: Literal["left", "right"]) -> None:
        toggle_flip = 1 if direction == "right" else -1

        commands = [
                StmTurn(angle=toggle_flip * 45, speed=self.config.turn_speed),
                StmWiggle(),
                StmTurn(angle=toggle_flip * -45, speed=self.config.turn_speed),
                StmWiggle(),
                StmStraight(distance=20, speed=self.config.turn_speed),
                StmWiggle(),
                StmTurn(angle=toggle_flip * -45, speed=self.config.turn_speed),
                StmWiggle(),
                StmTurn(angle=toggle_flip * 45, speed=self.config.turn_speed),
                StmWiggle(),
            ]

        self.stm.send_stm_command(
            *commands
        )

        self.logger.info("Catching leftover commands")

        while self.stm.wait_receive(3):
            pass


        self.distance_to_backtrack += self.config.BYPASS_DISTANCE
        self._log_tracked_distances("bypass obstacle")

    def _go_around_obstacle(self, direction: Literal["left", "right"]):
        """
        Mainly used for second obstacle
        :param direction:
        :return:
        """
        self.logger.info("Entering GO AROUND OBSTACLE")
        toggle_flip = 1 if direction == "left" else -1

        hug_side:Literal["left","right"] = "left" if direction != "left" else "right"

        commands = [
                StmTurn(angle=toggle_flip * -90, speed=self.config.turn_speed),
                StmWiggle(),
                StmSideHug(hug_side, threshold=60, speed=self.config.turn_speed),
                StmTurn(angle=toggle_flip * 180, speed=self.config.turn_speed),
                StmWiggle(),
                StmWiggle(),
                StmWiggle(),
                StmMoveUntilSideObstacle(side=hug_side, threshold=60, speed=self.config.turn_speed)
            ]

        self.stm.send_stm_command_and_wait(*commands)

        # Start measuring distance of the obstacle
        self.stm.send_stm_command(StmToggleMeasure())
        self.stm.wait_receive()

        # Move to end of obstacle
        self.stm.send_stm_command_and_wait(StmSideHug(hug_side, threshold=60, speed=self.config.turn_speed))

        # Get distance covered
        self.stm.send_stm_command(StmToggleMeasure())
        width = self._handle_distance_result(self.stm.wait_receive())
        self.config.OBSTACLE_WIDTH = width
        self._log_tracked_distances("go around obstacle")

        # Right turn
        self.stm.send_stm_command_and_wait(*[
            StmWiggle(),
            StmTurn(angle=toggle_flip * 90, speed=self.config.turn_speed),
            StmWiggle(),
            StmWiggle(),
            StmWiggle()
        ])







    """
    STEP Methods
    one -> Move first obstacle
    two -> Bypass first obstacle
    three -> Move to second obstacle
    four -> Go around second obstacle
    five -> Backtrack sufficient distance and maneuver back into carpark
    """

    def _test(self) -> None:
        for _ in range(5):
            self.stm.send_stm_command_and_wait(StmSideHug(threshold=60, speed=40, side="right"))

    def _step_one(self) -> None:
        """
        STEP ONE
        Method to move to fist obstacle
        1. Move to threshold distance to capture image
        2. Sends CV request
        :return:
        """
        self.logger.info("Executing STEP ONE")


        # Move to obstacle
        self._move_forward_to_distance(50)

        # Send CV request and pass step two as callback
        self.cm.slave_request_cv(Camera().capture(), self._step_two, ignore_bullseye=True)

    def _step_two(self, response: CvResponse) -> None:
        """
        STEP TWO
        Method to handle image response, then navigate the robot around the first obstacle
        1. Determine direction to go
        2. Navigate around obstacle to be inline with
        :param response:
        :return:
        """
        self.logger.info("Executing STEP TWO")

        if response.label not in [ObstacleLabel.Shape_Left, ObstacleLabel.Shape_Right]:
            self.logger.error("Direction arrow not captured!")
            # self.cm.slave_request_cv(Camera().capture(), self._step_two, ignore_bullseye=True)
        else:
            direction: Literal["left", "right"] = (
                "left" if response.label == ObstacleLabel.Shape_Left else "right"
            )
            self._bypass_obstacle(direction)
            self.distance_to_backtrack += (self.config.BYPASS_DISTANCE//2) + 10
            self._log_tracked_distances("End of step two")
            self._step_three()

    def _step_three(self) -> None:
        """
        STEP THREE
        1. Move to threshold distance
        2. Capture image and call step four callback
        :return:
        """
        self.logger.info("Executing STEP THREE")

        # Move to threshold distance
        self.stm.send_stm_command_and_wait(StmStraight(5, 30, False))

        self.stm.send_stm_command(StmToggleMeasure())
        self.stm.wait_receive()

        self._move_forward_to_distance(self.config.STEP_THREE_CLOSEUP_DISTANCE)

        # Record distance between both obstacles
        self.stm.send_stm_command(StmToggleMeasure())
        distance_moved = self._handle_distance_result(self.stm.wait_receive())
        self.distance_to_backtrack += distance_moved
        self._log_tracked_distances("After tracking step three")


        self._move_backwards_to_distance(self.config.STEP_THREE_CLOSEUP_DISTANCE)

        # Account for additional distance to account for
        self.distance_to_backtrack += self.config.STEP_THREE_CLOSEUP_DISTANCE
        self._log_tracked_distances("step three close up distance")

        # Move back to safe turning distance
        self._move_backwards_to_distance(30)

        # Capture image and send callback
        self.cm.slave_request_cv(Camera().capture(), self._step_four, ignore_bullseye=True)

    def _step_four(self, response: CvResponse) -> None:
        """
        STEP FOUR
        1. Capture image
        2. Bypass second obstacle
        :param response:
        :return:
        """
        self.logger.info("Executing STEP FOUR")

        if response.label not in [ObstacleLabel.Shape_Left, ObstacleLabel.Shape_Right]:
            self.logger.error("Direction arrow not captured!")
            # self.cm.slave_request_cv(Camera().capture(), self._step_four, ignore_bullseye=True)
        else:
            direction: Literal["left", "right"] = (
                "left" if response.label == ObstacleLabel.Shape_Left else "right"
            )
            self._go_around_obstacle(direction)
            self._step_five(direction)

    def _step_five(self, arrow_direction: Literal["left", "right"]) -> None:
        """
        STEP FIVE
        1. Backtrack distance before aligning with carpark
        2. Align with carpark
        3. Move into carpark
        :return:
        """
        self.logger.info("Executing STEP FIVE")

        """
        If the original arrow direction is LEFT, then the car will have to turn right before turning left
        in order to line up with the carpark
        """
        toggle_flip = 1 if arrow_direction == "left" else -1

        offset_distance = max(int((2 ** 0.5) * (self.config.OBSTACLE_WIDTH / 2)) - 15, 0)
        backtrack_distance = self.distance_to_backtrack - 30  # distance before making first 45deg turn

        self._log_tracked_distances("Performing backtrack")

        self.logger.info(f"OFFSET DISTANCE: {offset_distance}")
        self.logger.info(f"BACKTRACK: {backtrack_distance}")

        self.stm.send_stm_command(
            *[
                StmWiggle(),
                # Move backtrack distance
                StmStraight(
                    distance=backtrack_distance, speed=self.config.forward_speed
                ),
                # Align with car park
                StmTurn(angle=toggle_flip * 45, speed=self.config.turn_speed),
                StmWiggle(),
                StmStraight(distance=offset_distance, speed=self.config.turn_speed),
                StmWiggle(),
                StmTurn(angle=toggle_flip * -45, speed=self.config.turn_speed),
                # Close into car park
                StmMoveToDistance(distance=20),
            ]
        )

    def _complete(self) -> None:
        """
        Method to send the complete message to the android
        :return:
        """
        self.logger.info("Executing COMPLETE")
        self.end_callback()
        # self.android.send(AndroidMessage("status", "finish"))

    """
    ENTRYPOINT
    """

    def run(self, callback:Callable[[], None] = lambda: None) -> None:

        self.distance_to_backtrack = 0
        self.config = self.ConfigManeuver()

        self.end_callback = callback
        self._step_one()
        # self._test()
