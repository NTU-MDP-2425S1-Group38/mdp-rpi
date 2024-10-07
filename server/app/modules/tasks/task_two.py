import logging
from typing import Literal

from app_types.primatives.cv import CvResponse
from app_types.primatives.obstacle_label import ObstacleLabel
from modules.camera.camera import Camera
from modules.serial import STM
from modules.serial.stm_commands import StmMoveToDistance, StmMove, StmWiggle, StmToggleMeasure, StmTurn, StmStraight
from modules.web_server.connection_manager import ConnectionManager
from utils.metaclass.singleton import Singleton


class TaskTwoRunner(metaclass=Singleton):
    """
    Class to run task two logic
    """

    class ConfigManeuver:
        front_distance_threshold: int = 30
        turn_front_distance_threshold: int = 30

        forward_speed: int = 70
        turn_speed: int = 40

        SERVO_TURN_ANGLE = 25

        BYPASS_DISTANCE: int = 105  # Distance used to bypass an obstacle

    def __init__(self):
        self.logger = logging.getLogger("TaskTwoRunner")
        self.cm = ConnectionManager()
        self.stm = STM()
        self.stm.connect()
        self.config = self.ConfigManeuver()

        """
        Keeps track of distance the robot has to move in a straight line before allowing to turn back in line
        with the carpark.
        """
        self.distance_to_backtrack:int = 0

    """
    HELPER METHODS
    """


    def _wiggle_servo(self) -> None:
        """
        Wiggle servo to center
        :return: None
        """
        self.stm.send_stm_command(StmWiggle())

    def _move_to_front_threshold(self) -> None:
        """
        Move forward until the "front_distance_threshold"
        :return:
        """
        self.stm.send_stm_command(
            StmMoveToDistance(self.config.front_distance_threshold)
        )

    def _move_backwards_to_safe_turn_threshold(self) -> None:
        """
        Move backwards until a safe distance to maneuver.
        Assumes that the robot is already at front_distance_threshold
        :return:
        """
        self.stm.send_stm_command(
            StmMoveToDistance(self.config.turn_front_distance_threshold, forward=False)
        )

    def _bypass_obstacle(self, direction:Literal["left", "right"]) -> None:
        toggle_flip = 1 if direction=="right" else -1

        self.stm.send_stm_command(*[
            StmTurn(
                angle=toggle_flip * 45,
                speed=self.config.turn_speed
            ),
            StmWiggle(),
            StmTurn(
                angle=toggle_flip * -90,
                speed=self.config.turn_speed
            ),
            StmWiggle(),
            StmTurn(
                angle=toggle_flip * 45,
                speed=self.config.turn_speed
            ),
            StmWiggle()
        ])

    def _go_around_obstacle(self, direction:Literal["left", "right"]):
        """
        Mainly used for second obstacle
        :param direction:
        :return:
        """
        toggle_flip = 1 if direction=="left" else -1

        self.stm.send_stm_command(*[
            StmTurn(
                angle=toggle_flip * -70,
                speed=self.config.turn_speed
            ),
            StmWiggle(),
            StmTurn(
                angle=toggle_flip * 70,
                speed=self.config.turn_speed
            ),
            StmWiggle(),
            StmTurn(
                angle=toggle_flip * 90,
                speed=self.config.turn_speed
            ),
            StmWiggle(),
            StmStraight(
                distance=20, speed=self.config.turn_speed
            ),
            StmTurn(
                angle=toggle_flip * 90,
                speed=self.config.turn_speed
            ),
            StmWiggle()
        ])

    """
    STEP Methods
    one -> Move first obstacle
    two -> Bypass first obstacle
    three -> Move to second obstacle
    four -> Go around second obstacle
    five -> Backtrack sufficient distance
    six -> Slot back into carpark
    """

    def _test(self) -> None:
        self.stm.send_stm_command(
            StmMoveToDistance(10)
        )

    def _step_one(self) -> None:
        """
        STEP ONE
        Method to move to fist obstacle
        1. Tracks distance moved
        2. Sends CV request
        :return:
        """

        # Start tracking of distance
        self.stm.send_stm_command(StmToggleMeasure())

        # Move to obstacle
        self._move_to_front_threshold()

        # Get distance moved
        self.stm.wait_receive()  # Wait for full execution of movement
        self.stm.send_stm_command(StmToggleMeasure())
        distance = self.stm.wait_receive()
        print(distance)
        # TODO process distance

        # Send CV request and pass step two as callback
        self.cm.slave_request_cv(Camera().capture(), self._step_two)



    def _step_two(self, response: CvResponse) -> None:
        """
        STEP TWO
        Method to handle image response, then navigate the robot around the first obstacle
        1. Determine direction to go
        2. Navigate around obstacle to be inline with
        :param response:
        :return:
        """
        if response.label not in [ObstacleLabel.Shape_Left, ObstacleLabel.Shape_Right]:
            self.logger.error("Direction arrow not captured!")
            # self.cm.slave_request_cv(Camera().capture(), self._step_two, ignore_bullseye=True)
        else:
            direction: Literal["left","right"] = "left" if response.label == ObstacleLabel.Shape_Left else "right"
            self._bypass_obstacle(direction)
            self.stm.wait_receive()


    def _step_three(self) -> None:
        """
        STEP THREE
        1. Move to threshold distance
        2. Capture image and call step four callback
        :return:
        """

        # Move to threshold distance
        self.stm.send_stm_command(StmToggleMeasure())
        self._move_to_front_threshold()

        # Get distance moved
        self.stm.wait_receive()  # Wait for full execution of movement
        self.stm.send_stm_command(StmToggleMeasure())
        distance = self.stm.wait_receive()
        print(distance)
        # TODO process distance

        # Capture image and send callback
        self.cm.slave_request_cv(Camera().capture(),self._step_four)


    def _step_four(self, response: CvResponse) -> None:
        """
        STEP FOUR
        1. Capture image
        2. Bypass second obstacle
        :param response:
        :return:
        """

        if response.label not in [ObstacleLabel.Shape_Left, ObstacleLabel.Shape_Right]:
            self.logger.error("Direction arrow not captured!")
            # self.cm.slave_request_cv(Camera().capture(), self._step_four, ignore_bullseye=True)
        else:
            direction: Literal["left", "right"] = "left" if response.label == ObstacleLabel.Shape_Left else "right"
            self._go_around_obstacle(direction)
            self.stm.wait_receive()

    def _step_five(self) -> None:
        """
        STEP FIVE
        1. Calculate and backtrack distance before slotting in
        :return:
        """
        distance_to_backtrack = self.distance_to_backtrack
        self.stm.send_stm_command(
            StmMove(distance=distance_to_backtrack)
        )
        self.stm.wait_receive()
        self._step_six()

    def _step_six(self) -> None:
        """
        STEP SIX
        1. Align with carpark
        :return:
        """
        self.stm.send_stm_command()
        self.stm.wait_receive()

    def _step_seven(self) -> None:
        """
        STEP SEVEN
        1. Move to carpark
        :return:
        """
        self._move_to_front_threshold()


    """
    ENTRYPOINT
    """

    def run(self) -> None:
        self._step_three()





