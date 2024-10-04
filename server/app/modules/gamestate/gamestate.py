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
from modules.serial import STM, Android
from modules.serial.android import AndroidMessage
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
    Methods related to checklist task a5.
    """

    def _run_task_checklist_a5(self) -> None:
        """
        Method to run task a5.
        Obstacles need to be set and instructions need to be added prior to running.
        :return: None
        """
        self.stm.connect()
        self.logger.info("Starting task A5")
        count = [0]  # Using a list to store count, as it's mutable

        def move_to_next_face_and_capture(cv_res: CvResponse) -> None:
            # Access count from the outer scope
            if cv_res.label in [
                ObstacleLabel.Unknown,
                ObstacleLabel.Shape_Bullseye,
            ]:
                if count[0] > 2:
                    return
                self.logger.info(
                    f"Label not detected! Moving to next face! Count: {count[0]}"
                )

                # Move to next face
                self.stm.send_cmd("t", 55, 0, 85)
                self.stm.send_cmd("T", 55, 25, 89)
                while True:
                    message_rcv = self.stm.wait_receive()
                    print(message_rcv)
                    if message_rcv[0] == "f":
                        break

                self.stm.send_cmd("T", 55, -25, 0)
                while True:
                    message_rcv = self.stm.wait_receive()
                    print(message_rcv)
                    if message_rcv[0] == "f":
                        break
                time.sleep(1)
                # Original
                self.stm.send_cmd("T", 55, -25, 88)
                self.stm.send_cmd("T", 55, -25, 88)

                # Experiment
                # self.stm.send_cmd("t", 35, -25, 88)
                # self.stm.send_cmd("t", 35, -25, 88)
                self.logger.info("Commands sent, waiting for completion!")

                f_count = 0
                while True:
                    message_rcv = self.stm.wait_receive()
                    print(message_rcv)
                    if message_rcv[0] == "f":
                        f_count += 1
                    if f_count == 3:
                        break

                self.logger.info("Commands completed, taking picture!")
                count[0] += 1  # Increment count
                self.capture_and_process_image(move_to_next_face_and_capture)

        self.logger.info("Initiating and moving forward to objective")
        self.stm.send_cmd("T", 55, 0, 10)
        self.logger.info("Commands sent, waiting for completion!")

        while True:
            message_rcv = self.stm.wait_receive()
            print(message_rcv)
            if message_rcv[0] == "f":
                break

        self.logger.info("Commands completed, taking picture!")
        self.capture_and_process_image(move_to_next_face_and_capture)

        self.logger.info("Task A5 completed!")
        return

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

    def _stop_task_one(self):
        """Stops all processes on the RPi and disconnects from Android, STM and PC"""
        time.sleep(0.2)
        self.android.send("STOP")
        print("Program Ended\n")

    """
    Methods related to task 2.
    """

    def _run_task_two(self) -> None:
        pass


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
        elif task == 2:
            self._run_task_two()
