import logging
from collections.abc import Callable
from typing import Literal, List, Optional
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
from app_types.primatives.obstacle_direction import ObstacleDirection
from app_types.primatives.position import Position
from utils.instructions import Instructions
from modules.camera.camera import Camera

# from modules.serial.stm32 import STM
from modules.web_server.connection_manager import ConnectionManager
from utils.metaclass.singleton import Singleton


class GameState(metaclass=Singleton):
    """
    Singleton class for holding onto the game state.
    """

    logger = logging.getLogger("GameState")

    camera: Camera
    connection_manager: ConnectionManager
    # stm: STM

    obstacles: List[Obstacle] = []
    instruction: Instructions = Instructions()

    def __init__(self):
        self.logger.info("Initialising camera")
        # self.camera = Camera()

        self.logger.info("Initialising connection manager")
        self.connection_manager = ConnectionManager()

        self.STM_Stopped = False

        # self.logger.info("Initialising STM connector")
        # self.stm = STM()

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

        # TODO update android of updated label

    def capture_and_update_label(self, obstacle_id: int) -> None:
        self.capture_and_process_image(
            lambda res: self._update_obstacle_label_after_cv(obstacle_id, res)
        )

    def stitch_images():
        """
        Method to stitch images together.
        """
        pass

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
        self.connection_manager.slave_request_algo(
            self.obstacles, self._algo_response_callback
        )

    """
    Methods related to checklist task a5.
    """

    def _run_task_checklist(self) -> None:
        """
        Method to run task a5.
        Obstacles need to be set and instructions need to be added prior to running.
        :return: None
        """
        self.logger.info("Starting task A5")
        image_id = None
        stm = self.stm

        while True:
            # South to East to North to West

            # Move forward to South
            stm.send_cmd("T", 55, 90, 20)

            self.capture_and_process_image(1)
            if image_id != "bullseye":
                break
            # Move to East

            self.capture_and_process_image(1)
            if image_id != "bullseye":
                break
            # Move to North

            self.capture_and_process_image(1)
            if image_id != "bullseye":
                break

            # Move to West
            self.capture_and_process_image(1)
            if image_id != "bullseye":
                break

        self.logger("Task a5 completed!")

    """
    Methods related to task 1.
    """

    def set_stm_stop(self, val) -> None:
        self.STM_Stopped = val

    def get_stm_stop(self) -> bool:
        return self.STM_Stopped

    def _run_task_one(self) -> None:
        """
        Method to run task one.
        Obstacles need to be set and instructions need to be added prior to running.
        :return: None
        """
        start_time = 0
        drive_speed = 55
        drive_angle = 25

        self.logger.info("Starting task one running loop!")
        self.set_stm_stop(False)  # Reset to false upon starting the new segment
        count = 0
        while cmd := self.instruction.pop():
            self.logger.info(f"Current command: {cmd.model_dump()}")
            angle = 0
            val = 0

            if isinstance(cmd.value, MoveInstruction):
                move_direction = cmd.move.value
                angle = 0
                val = cmd.amount
                self.logger.info(f"AMOUNT TO MOVE: {val}")
                self.logger.info(f"MOVE DIRECTION: {move_direction}")

                if move_direction == "FORWARD":
                    flag = "T"
                elif move_direction == "BACKWARD":
                    flag = "t"
            else:
                if (
                    isinstance(cmd.value, CommandInstruction)
                    and cmd.value == "CAPTURE_IMAGE"
                ):
                    flag = "S"
                    count += 1

                elif isinstance(cmd.value, TurnInstruction):
                    val = 90
                    if cmd.value == "FORWARD_LEFT":
                        flag = "T"
                        angle = -drive_angle
                    elif cmd.value == "FORWARD_RIGHT":
                        flag = "T"
                        angle = drive_angle
                    elif cmd.value == "BACKWARD_LEFT":
                        flag = "t"
                        angle = -drive_angle

            self.stm.send_cmd(flag, drive_speed, angle, val)

            self.logger.info("STM Command sent successfully...")
            while not self.get_stm_stop():
                # Wait until the STM has execute all the commands and stopped (True), then wait x seconds to recognise image
                pass

            time.sleep(0.75)
            print("STM stopped, sending time of capture...")
            self.pc.send(f"DETECT,{cmd.capture_id}")

        print(
            f">>>>>>>>>>>> Completed in {(time.time_ns() - start_time) / 1e9:.2f} seconds."
        )

        # try:
        #     print("request stitch")
        #     self.pc.send(f"PERFORM STITCHING,{count}")
        # except OSError as e:
        #     print("Error in sending stitching command to PC: " + e)

        self.logger.info("Run Task One completed!")

        self.stop()

    """
    Methods related to task 2.
    """

    def sin_deg(angle):
        return math.sin(angle * math.pi / 180)

    def cos_deg(angle):
        return math.cos(angle * math.pi / 180)

    def _run_task_two(self, config) -> None:
        """
        Method to run task two.
        Obstacles need to be set and instructions need to be added prior to running.
        :return: None
        """
        num_M = 0
        num_obstacle = 1
        is_right1 = False  # track whether first obstacle was a left or right turn
        is_right2 = False  # track whether second obstacle was a left or right turn
        done_obstacle2 = False  # track whether second arrow was seen

        on_arrow_callback = (
            None  # callback that takes in a single argument, boolean is_right
        )

        capture_dist1 = 30  # distance between first arrow and where car will stop.
        capture_dist2 = 20  # distance between second arrow and where car will stop.
        obstacle_dist1 = None  # distance between carpark and first obstacle.
        obstacle_dist2 = None  # distance between carpark and second obstacle.
        wall_dist = None  # distance driven to face wall after second obstacle.
        wall_complete = False  # signal wall has been tracked.
        obstacle2_length_half = None  # length of obstacle.

        turning_r = 40  # turning radius
        r0 = 21  # absolute distance from center line after passing obstacle 1
        chassis_cm = 15  # length from axle to axle
        wheelbase_cm = 16.5  # length between front wheels

        # tune to balance speed with precision. kachow!
        if config.is_outdoors:
            theta2 = 10  # angle to face second obstacle after first arc.
            drive_speed = 35
            obstacle_speed = 45
            wall_track_speed = 35
            carpark_speed = 45
        else:
            theta2 = 10  # angle to face second obstacle after first arc.
            drive_speed = 45
            obstacle_speed = 50
            wall_track_speed = 45
            carpark_speed = 30

        # left and right arrow IDs
        self.LEFT_ARROW_ID = "39"
        self.RIGHT_ARROW_ID = "38"

        self.logger.info("Run Task Two completed!")

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
            self._run_task_one()

    def stop(self):
        """Stops all processes on the RPi and disconnects from Android, STM and PC"""
        time.sleep(0.2)
        self.android.send("STOP")
        # self.android.disconnect()
        # self.stm.disconnect()
        # self.pc.disconnect()
        # TODO: Add Stream disconnect/end
        print("Program Ended\n")
