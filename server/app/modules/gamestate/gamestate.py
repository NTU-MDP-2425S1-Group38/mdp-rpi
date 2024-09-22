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
from modules.serial import STM
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
        self.logger.info("Initialising connection manager")
        self.connection_manager = ConnectionManager()

        self.logger.info("Initialising STM connector")
        self.stm = STM()

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

        # TODO update android of updated label

    def capture_and_update_label(self, obstacle_id: int) -> None:
        self.capture_and_process_image(
            lambda res: self._update_obstacle_label_after_cv(obstacle_id, res)
        )

    def stitch_images(self):
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
                self.stm.send_cmd("T", 55, 25, 87)
                while True:
                    message_rcv = self.stm.wait_receive()
                    print(message_rcv)
                    if message_rcv[0] == "f":
                        break

                self.stm.send_cmd("T", 55, -25, 0)
                self.stm.send_cmd("T", 55, -25, 90)
                self.stm.send_cmd("T", 55, -25, 90)
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
        # self.stm.send_cmd("T", 55, 0, 10)
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

    def send_M(self):
        self.stm.send_cmd("M", 0, 0, 0)

    def send_D(self):
        self.stm.send_cmd("D", 0, 0, 0)

    def drive(self, angle, val, is_forward=True, speed=None):
        if speed is None:
            speed = self.drive_speed

        if val < 0:
            val = -val
            is_forward = not is_forward

        self.stm.send_cmd("T" if is_forward else "t", speed, angle, val)

    def drive_until(self, angle, val, is_forward=True, speed=None):
        if speed is None:
            speed = self.drive_speed

        self.stm.send_cmd("W" if is_forward else "w", speed, angle, val)

    def wall_ride(self, angle, is_right, threshold=30, is_forward=True, speed=None):
        if speed is None:
            speed = self.drive_speed

        char = "R" if is_right else "L"
        if not is_forward:
            char = char.lower()

        self.stm.send_cmd(char, speed, angle, threshold)

    def calc_arc(self, x, y):
        is_right = x >= 0
        if not is_right:
            x = -x

        r = (x**2 + y**2) / (2 * x)  # turning radius to execute.
        angle = (
            math.atan(self.chassis_cm / (r - self.wheelbase_cm / 2)) * 180 / math.pi
        )  # calculate steering angle.
        theta = (
            math.atan(y / (r - x)) * 180 / math.pi
        )  # resultant facing angle after turn.
        if angle > 25:
            angle = 25
        if not is_right:
            angle = -angle

        return angle, theta

    # drive towards obstacle (and insert 'D' to signal distance tracking).
    def perform_toward_obstacle(self, capture_dist=30) -> None:
        # self.stm.send_cmd("W", self.drive_speed, 0, 50)
        self.send_D()
        self.drive_until(0, capture_dist, speed=self.obstacle_speed)
        self.send_D()

    # drive until IR sensor is above threshold (and insert 'D' for distance tracking).
    def perform_wall_track(
        self, is_right, is_forward=True, threshold=30, should_track=False
    ) -> None:
        if should_track:
            self.send_D()

        self.wall_ride(
            0,
            is_right,
            is_forward=is_forward,
            threshold=threshold,
            speed=self.wall_track_speed,
        )
        if should_track:
            self.send_D()

    # drive arc for first 10x10 obstacle.
    def perform_arc1(self, is_right) -> None:
        # mark image seen.

        # get initial turning angle.
        angle = 25 if is_right else -25

        turn_theta = 33
        self.drive(angle, turn_theta)
        self.drive(0, 18)
        self.drive(-angle, turn_theta + self.theta2)
        self.send_M()
        self.set_last_image(None)

    # drive arc for second 60x10 obstacle.
    def perform_arc2(self, is_right1, is_right2) -> None:
        is_cross = is_right1 != is_right2
        angle = 25 if is_right2 else -25

        # while self.obstacle_dist2 is None:
        #     pass

        # turn to be parallel to the second obstacle.
        if is_cross:
            gamma = 25
            self.drive(0, 10)
            self.drive(-angle, gamma, False)
            self.drive(angle, 90 - gamma - self.theta2)
        else:
            gamma = 37
            delta = self.theta2 * 1.7
            self.drive(angle, self.theta2 + delta)
            self.drive(-angle, gamma, False)
            self.drive(angle * 0.8, 90 - gamma - delta)

        # use wall tracking to find wall.
        wall_is_right = not is_right2
        self.perform_wall_track(wall_is_right, is_forward=False, threshold=-50)
        self.perform_wall_track(wall_is_right, is_forward=True, threshold=50)

        self.stm.send_cmd("S", 0, 0, 0)  # Command to stop the Robot

        self.drive(-angle, 180)
        self.perform_wall_track(
            wall_is_right, is_forward=True, threshold=50, should_track=True
        )
        # wait for wall distance to be calculated.
        while not self.wall_complete:
            pass

        print(f"----------------- Wall distance: {self.wall_dist:.3f}cm --------------")
        self.drive(-angle, 90)

    # sends arrow message to android.
    def send_arrow_android(self, obstacle_num, is_right):
        self.android.send(f"ARROW,{obstacle_num},{'R' if is_right else 'L'}")

    # set this callback it is time to detect an arrow for obstacle 1.
    def callback_obstacle1(self, is_right) -> None:
        self.send_arrow_android(1, is_right)
        with self.lock:
            self.is_right1 = is_right

        self.perform_arc1(is_right)
        self.perform_toward_obstacle()

        self.on_arrow_callback = None  # clear callback.

    # set this callback it is time to detect an arrow for obstacle 2.
    def callback_obstacle2(self, is_right) -> None:
        self.send_arrow_android(2, is_right)
        with self.lock:
            self.done_obstacle2 = True
            self.is_right2 = is_right

        self.perform_arc2(self.is_right1, is_right)
        self.on_arrow_callback = None  # clear callback.

        self.perform_carpark()

    # drive back to the carpark.
    def perform_carpark(self) -> None:
        while (
            self.obstacle_dist1 is None
            or self.obstacle_dist2 is None
            or not self.wall_complete
        ):
            pass

        angle = -25
        if self.is_right2:
            angle = 25

        y1 = (self.obstacle_dist2 + self.chassis_cm + self.capture_dist2) * math.cos(
            self.theta2 * math.pi / 180
        )
        y2 = self.obstacle_dist1 + self.chassis_cm / 2 + self.capture_dist1

        print(f"y1: {y1}, y2: {y2}")
        d1 = 0.7 * y1
        self.drive(0, d1)
        a, d = self.calc_arc(
            self.wall_dist / 2 + self.wheelbase_cm, y1 - d1 + y2 - self.turning_r * 0.25
        )
        print(f"a: {a}, d: {d}")
        self.drive(-a if self.is_right2 else a, d)
        # self.drive(-angle, 90 - d)

        gamma = 30
        self.drive(angle, gamma, is_forward=False)
        self.drive(-angle, 90 - gamma - d)

        self.wall_ride(0, self.is_right2, is_forward=False, threshold=-45)
        self.wall_ride(0, self.is_right2, threshold=45)
        # self.drive(angle, d)
        self.drive(angle, 90)
        self.drive_until(
            0, 15, speed=self.carpark_speed
        )  # slowly advance into carpark.
        self.send_M()  # signal stop.

    def _run_task_two(self, config) -> None:
        """
        Method to run task two.
        Obstacles need to be set and instructions need to be added prior to running.
        :return: None
        """

        self.logger.info("Starting program...")
        self.logger.info("Sending initial commands to the STM32...")
        self.start_time = time.time_ns()
        self.perform_toward_obstacle(self.capture_dist1)

        self.logger.info("Run Task Two completed!")

    def _stop_task_two(self):
        """Stops all processes on the RPi and disconnects from Android, STM and PC"""
        self.android.send("STOP")  # stop the Android tablet.
        self.pc.send("STITCH")  # request a stitch.

        print(
            f">>>>>>>>>> Ended: {(time.time_ns() - self.start_time) / 1e9:.3f}s. -------------- !"
        )

    """
    Main entry methods
    """

    def run(self, task: Literal[1, 2]) -> None:
        """
        Method to start execution.
        :param task: Literal[1, 2] corresponding to which task
        :return: None
        """
        self._run_task_checklist_a5()

        if task == 1:
            self._run_task_one()
        elif task == 2:
            self._run_task_two(None)
