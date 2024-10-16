#!/usr/bin/env python3
import json
import queue
import time
from multiprocessing import Manager, Process
from typing import Optional

import requests
from logger import prepare_logger
from modules.camera.camera import Camera
from modules.serial.android import Android
from modules.serial.stm32 import STM

API_IP = "192.168.100.194"
API_PORT = 8000

obstacle_direction = {
    "NORTH": 1,
    "SOUTH": 2,
    "EAST": 3,
    "WEST": 4,
}

direction_obstacle = {
    1: "NORTH",
    2: "SOUTH",
    3: "EAST",
    4: "WEST",
}

# Need to Fix
SYMBOL_MAP = {
    "Bullseye": "10",
    "One": "11",
    "Two": "12",
    "Three": "13",
    "Four": "14",
    "Five": "15",
    "Six": "16",
    "Seven": "17",
    "Eight": "18",
    "Nine": "19",
    "A": "20",
    "B": "21",
    "C": "22",
    "D": "23",
    "E": "24",
    "F": "25",
    "G": "26",
    "H": "27",
    "S": "28",
    "T": "29",
    "U": "30",
    "V": "31",
    "W": "32",
    "X": "33",
    "Y": "34",
    "Z": "35",
    "UP": "36",
    "DOWN": "37",
    "RIGHT": "38",
    "LEFT": "39",
    "CIRCLE": "40",
}


class PiAction:
    """
    Class that represents an action that the RPi needs to take.
    """

    def __init__(self, cat, value):
        """
        :param cat: The category of the action. Can be 'info', 'mode', 'path', 'snap', 'obstacle', 'location', 'failed', 'success'
        :param value: The value of the action. Can be a string, a list of coordinates, or a list of obstacles.
        """
        self._cat = cat
        self._value = value

    @property
    def cat(self):
        return self._cat

    @property
    def value(self):
        return self._value


# Example: Prepend item to the start of the queue
def prepend_to_queue(queue, item):
    # Extract all existing items from the queue
    temp_items = []
    while not queue.empty():
        temp_items.append(queue.get())

    # Add the new item at the start
    queue.put(item)

    # Add back all the other items in the original order
    for temp_item in temp_items:
        queue.put(temp_item)


class Task1RPI:
    """
    Class that represents the Raspberry Pi.
    """

    def __init__(self, config):
        self.config = config
        self.logger = prepare_logger()
        self.android = Android()
        self.stm = STM()

        self.manager = Manager()

        self.android_dropped = self.manager.Event()
        self.unpause = self.manager.Event()

        self.movement_lock = self.manager.Lock()

        self.android_queue = self.manager.Queue()  # Messages to send to Android
        # Messages that need to be processed by RPi
        self.rpi_action_queue = self.manager.Queue()
        # Messages that need to be processed by STM32, as well as snap commands
        self.command_queue = self.manager.Queue()
        # X,Y,D coordinates of the robot after execution of a command
        self.path_queue = self.manager.Queue()

        self.proc_recv_android = None
        self.proc_recv_stm32 = None
        self.proc_android_sender = None
        self.proc_command_follower = None
        self.proc_rpi_action = None
        self.rs_flag = False
        self.success_obstacles = self.manager.list()
        self.failed_obstacles = self.manager.list()
        self.obstacles = self.manager.dict()
        self.current_location = self.manager.dict()
        self.failed_attempt = False

        self.robot_x = 0
        self.robot_y = 0
        self.robot_d = "EAST"

        self.obstacle_dict = {}  # Obstacle Dict
        self.robot = None  # Robot
        self.prev_image = None

        self.last_image = None
        self.prev_image = None
        self.STM_Stopped = False

        self.start_time = 0
        self.drive_speed = 40 if config.is_outdoors else 55
        self.drive_angle = 25

    # Done
    def start(self):
        """Starts the RPi orchestrator"""
        try:
            ### Start up initialization ###

            self.android.connect()
            self.android_queue.put("info, You are connected to the RPi!")
            self.stm.connect()
            self.check_api()

            # Define child processes
            self.proc_recv_android = Process(target=self.recv_android)
            self.proc_recv_stm32 = Process(target=self.recv_stm)
            self.proc_android_sender = Process(target=self.android_sender)
            self.proc_command_follower = Process(target=self.command_follower)
            self.proc_rpi_action = Process(target=self.rpi_action)

            # Start child processes
            self.proc_recv_android.start()
            self.proc_recv_stm32.start()
            self.proc_android_sender.start()
            self.proc_command_follower.start()
            self.proc_rpi_action.start()

            self.logger.info("Child Processes started")

            ### Start up complete ###

            # Send success message to Android
            self.android_queue.put("info, Robot is ready!")
            # self.android_queue.put("mode, path")
            self.reconnect_android()

        except KeyboardInterrupt:
            self.stop()

    # Done
    def stop(self):
        """Stops all processes on the RPi and disconnects gracefully with Android and STM32"""
        self.android.disconnect()
        self.stm.disconnect()
        self.logger.info("Program exited!")

    # Done
    def reconnect_android(self):
        """Handles the reconnection to Android in the event of a lost connection."""
        self.logger.info("Reconnection handler is watching...")

        while True:
            # Wait for android connection to drop
            self.android_dropped.wait()

            self.logger.error("Android link is down!")

            # Kill child processes
            self.logger.debug("Killing android child processes")
            self.proc_android_sender.kill()
            self.proc_recv_android.kill()

            # Wait for the child processes to finish
            self.proc_android_sender.join()
            self.proc_recv_android.join()
            assert self.proc_android_sender.is_alive() is False
            assert self.proc_recv_android.is_alive() is False
            self.logger.debug("Android child processes killed")

            # Clean up old sockets
            self.android.disconnect()

            # Reconnect
            self.android.connect()

            # Recreate Android processes
            self.proc_recv_android = Process(target=self.recv_android)
            self.proc_android_sender = Process(target=self.android_sender)

            # Start previously killed processes
            self.proc_recv_android.start()
            self.proc_android_sender.start()

            self.logger.info("Android child processes restarted")
            # self.android_queue.put("info, You are reconnected!")
            # self.android_queue.put("mode, path")

            self.android_dropped.clear()

    # Done
    def recv_android(self) -> None:
        """
        [Child Process] Processes the messages received from Android
        """
        while True:
            msg_str: Optional[str] = None
            try:
                msg_str = self.android.receive()
            except OSError:
                self.android_dropped.set()
                self.logger.debug("Event set: Android connection dropped")

            if msg_str is None:
                continue

            messages = msg_str.split("\n")

            for message_rcv in messages:
                ## Command: Set obstacles ##
                if "OBSTACLE" in message_rcv:
                    self.logger.info("OBSTACLE!!!!")
                    id, x, y, dir = message_rcv.split(",")[1:]
                    id = int(id)

                    if dir == "-1":
                        if id in self.obstacle_dict:
                            del self.obstacle_dict[id]
                            self.logger.info("Deleted obstacle", id)
                    elif dir not in ["NORTH", "SOUTH", "EAST", "WEST"]:
                        self.logger.info(
                            f"Invalid direction provided: {dir}, ignoring..."
                        )
                        continue
                    else:
                        newObstacle = {
                            "id": id,
                            "x": int(x),
                            "y": int(y),
                            "d": obstacle_direction[dir],
                        }
                        self.obstacle_dict[id] = newObstacle

                        self.logger.info("Obstacle set successfully: ", newObstacle)
                    self.logger.info(
                        f"--------------- Current list {len(self.obstacle_dict)}: -------------"
                    )
                    obs_items = self.obstacle_dict.items()
                    if len(obs_items) == 0:
                        self.logger.info("! no obstacles.")
                    else:
                        for id, obstacle in obs_items:
                            self.logger.info(f"{id}: {obstacle}")

                elif "ROBOT" in message_rcv:
                    self.logger.info("NEW ROBOT LOCATION!!!")
                    x, y, dir = message_rcv.split(",")[1:]
                    x, y = int(x), int(y)

                    if x < 0 or y < 0:
                        self.logger.info("Illegal robot coordinate, ignoring...")
                        continue

                    self.robot = {"x": x, "y": y, "dir": dir}
                    self.logger.info("Robot set successfully: ", self.robot)

                elif "Calculate" in message_rcv:
                    if not self.check_api():
                        self.logger.error("API is down! Start command aborted.")
                        # self.android_queue.put(
                        #     "error, API is down, start command aborted."
                        # )

                    self.rpi_action_queue.put(
                        PiAction(
                            cat="obstacles", value=list(self.obstacle_dict.values())
                        )
                    )
                    self.logger.debug(
                        f"Set obstacles PiAction added to queue: {self.obstacle_dict}"
                    )

                    while self.command_queue.empty():
                        pass

                    # Commencing path following
                    if not self.command_queue.empty():
                        self.logger.debug("Calculated")

                elif "BEGIN" in message_rcv:
                    # if not self.check_api():
                    #     self.logger.error("API is down! Start command aborted.")
                    #     # self.android_queue.put(
                    #     #     "error, API is down, start command aborted."
                    #     # )

                    # self.rpi_action_queue.put(
                    #     PiAction(
                    #         cat="obstacles", value=list(self.obstacle_dict.values())
                    #     )
                    # )
                    # self.logger.debug(
                    #     f"Set obstacles PiAction added to queue: {self.obstacle_dict}"
                    # )

                    # while self.command_queue.empty():
                    #     pass

                    # Commencing path following
                    if not self.command_queue.empty():
                        # Main trigger to start movement #
                        self.unpause.set()
                        self.logger.info(
                            "Start command received, starting robot on path!"
                        )
                        # self.android_queue.put("info, Starting robot on path!")

                        # self.android_queue.put("status, running")
                    else:
                        self.logger.warning(
                            "The command queue is empty, please set obstacles."
                        )
                        # self.android_queue.put(
                        #     "error,Command queue is empty, did you set obstacles?",
                        # )

                elif "CLEAR" in message_rcv:
                    print(" --------------- CLEARING OBSTACLES LIST. ---------------- ")
                    self.obstacle_dict.clear()

                else:
                    # Catch for messages with no keywords (OBSTACLE/ROBOT/BEGIN)
                    self.logger.info(f"Not a keyword, message received: {message_rcv}")

    def recv_stm(self) -> None:
        """
        [Child Process] Receive acknowledgement messages from STM32, and release the movement lock
        """
        msg = ""
        while True:
            message = None

            try:
                message = self.stm.wait_receive()
                self.logger.info(f"Message received from STM: {message}")

                if message.startswith("fS"):
                    continue

                elif message[0] == "f":
                    # Finished command, send to android
                    message_split = message[1:].split(
                        "|"
                    )  # Ignore the 'f' at the start
                    cmd_speed = message_split[0]
                    turning_degree = message_split[1]
                    distance = message_split[2].strip()

                    cmd = cmd_speed[0]  # Command (t/T)

                    if (
                        turning_degree == f"-{self.drive_angle}"
                        or turning_degree == f"{self.drive_angle}"
                        or turning_degree == "0"
                    ):
                        print(self.robot_x, self.robot_y, self.robot_d)
                        msg = f"ROBOT|{self.robot_y},{self.robot_x},{self.robot_d}"
                    # if turning_degree == f"-{self.drive_angle}":
                    #     # Turn left
                    #     if cmd == "t":
                    #         # Backward left
                    #         msg = "TURN,BACKWARD_LEFT,0"
                    #     elif cmd == "T":
                    #         # Forward left
                    #         msg = "TURN,FORWARD_LEFT,0"
                    # elif turning_degree == f"{self.drive_angle}":
                    #     # Turn right
                    #     if cmd == "t":
                    #         # Backward right
                    #         msg = "TURN,BACKWARD_RIGHT,0"
                    #     elif cmd == "T":
                    #         # Forward right
                    #         msg = "TURN,FORWARD_RIGHT,0"
                    # elif turning_degree == "0":
                    #     if cmd == "t":
                    #         # Backward
                    #         msg = "MOVE,BACKWARD," + distance
                    #     elif cmd == "T":
                    #         # Forward
                    #         msg = "MOVE,FORWARD," + distance
                    else:
                        # Unknown turning degree
                        self.logger.info("Unknown turning degree")
                        msg = "No instruction"

                    if msg != "No instruction":
                        print(msg)
                        self.logger.info(f"Msg: {msg}")
                        self.android_queue.put(msg)
                        self.logger.info(f"SENT TO ANDROID SUCCESSFULLY: {msg}")
                    try:
                        self.movement_lock.release()
                        try:
                            self.retrylock.release()
                        except:
                            pass
                        self.logger.debug(
                            "ACK from STM32 received, movement lock released."
                        )
                        self.logger.info(
                            f"self.current_location = {self.current_location}"
                        )
                    except Exception:
                        self.logger.warning("Tried to release a released lock!")

                else:
                    self.logger.warning(f"Ignored unknown message from STM: {message}")
            except OSError:
                self.logger.error("Event set: STM32 dropped")
                self.stm_dropped.set()
                break

    # Done
    def android_sender(self) -> None:
        """
        [Child process] Responsible for retrieving messages from android_queue and sending them over the Android link.
        """
        while True:
            # Retrieve from queue
            try:
                message = self.android_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self.android.send(message)
            except OSError:
                self.android_dropped.set()
                self.logger.debug("Event set: Android dropped")

    def command_follower(self) -> None:
        """
        [Child Process]
        """
        while True:
            # Retrieve next movement command
            command: str = self.command_queue.get()
            self.logger.debug("wait for unpause")
            self.logger.debug(command)
            # Wait for unpause event to be true [Main Trigger]
            try:
                self.logger.debug("wait for retrylock")
                self.retrylock.acquire()
                self.retrylock.release()
            except:
                self.logger.debug("wait for unpause")
                self.unpause.wait()
            self.logger.debug("wait for movelock")
            # Acquire lock first (needed for both moving, and snapping pictures)
            self.movement_lock.acquire()

            angle = 0
            flag = ""
            val = 0

            if command == "WIGGLE":
                self.logger.info("WIGGLE")
                flag = "T"
                angle = -20
                val = 2
                # self.stm.send_cmd(flag, int(self.drive_speed), int(angle), int(val))
                self.stm.send_cmd("T", int(self.drive_speed), -20, 0)
            elif command != "WIGGLE":
                self.robot_x = command["end_position"]["x"]
                self.robot_y = command["end_position"]["y"]
                self.robot_d = direction_obstacle[command["end_position"]["d"]]

                print(self.robot_x, self.robot_y, self.robot_d)

                if isinstance(command["value"], dict) and command["value"]["move"] in [
                    "FORWARD",
                    "BACKWARD",
                ]:
                    move_direction = command["value"]["move"]
                    angle = 0
                    val = command["value"]["amount"]
                    self.logger.info(f"AMOUNT TO MOVE: {val}")
                    self.logger.info(f"MOVE DIRECTION: {move_direction}")

                    if move_direction == "FORWARD":
                        flag = "T"
                    elif move_direction == "BACKWARD":
                        flag = "t"

                    self.stm.send_cmd(flag, int(self.drive_speed), int(angle), int(val))

                elif command["value"] in [
                    "FORWARD_LEFT",
                    "FORWARD_RIGHT",
                    "BACKWARD_LEFT",
                    "BACKWARD_RIGHT",
                ]:
                    val = 90
                    if command["value"] == "FORWARD_LEFT":
                        flag = "T"
                        angle = -self.drive_angle
                    elif command["value"] == "FORWARD_RIGHT":
                        flag = "T"
                        angle = self.drive_angle
                    elif command["value"] == "BACKWARD_LEFT":
                        flag = "t"
                        angle = -self.drive_angle
                    elif command["value"] == "BACKWARD_RIGHT":
                        flag = "t"
                        angle = self.drive_angle
                    if (
                        command["value"] == "FORWARD_RIGHT"
                        or command["value"] == "BACKWARD_RIGHT"
                    ):
                        prepend_to_queue(self.command_queue, "WIGGLE")
                        prepend_to_queue(self.command_queue, "WIGGLE")
                        prepend_to_queue(self.command_queue, "WIGGLE")

                        self.stm.send_cmd(
                            flag, int(self.drive_speed), int(angle), int(val)
                        )
                        # self.stm.send_cmd("T", int(self.drive_speed), -20, 0)
                        # self.stm.send_cmd("T", int(self.drive_speed), -20, 0)
                        # self.stm.send_cmd("T", int(self.drive_speed), -20, 0)

                    else:
                        self.stm.send_cmd(
                            flag, int(self.drive_speed), int(angle), int(val)
                        )

                elif command["value"] == "CAPTURE_IMAGE":
                    flag = "S"
                    self.stm.send_cmd(flag, int(self.drive_speed), int(angle), int(val))
                    self.rpi_action_queue.put(
                        PiAction(cat="snap", value=command["capture_id"])
                    )

                # End of path (TBD)
                elif command["value"] == "FIN":
                    self.logger.info(
                        f"At FIN, self.failed_obstacles: {self.failed_obstacles}"
                    )
                    self.logger.info(
                        f"At FIN, self.current_location: {self.current_location}"
                    )
                    self.unpause.clear()
                    self.movement_lock.release()
                    self.logger.info("Commands queue finished.")
                    # self.android_queue.put("info, Commands queue finished.")
                    # self.android_queue.put("status, finished")
                    self.rpi_action_queue.put(PiAction(cat="stitch", value=""))
            else:
                raise Exception(f"Unknown command: {command}")

    # Done
    def rpi_action(self):
        """
        [Child Process]
        """
        while True:
            action: PiAction = self.rpi_action_queue.get()
            self.logger.debug(
                f"PiAction retrieved from queue: {action.cat} {action.value}"
            )
            # Done
            if action.cat == "obstacles":
                for obs in action.value:
                    self.obstacles[obs["id"]] = obs
                self.request_algo(action.value)
            elif action.cat == "snap":
                self.snap_and_rec(obstacle_id_with_signal=action.value)
            elif action.cat == "stitch":
                self.request_stitch()

    # Done
    def snap_and_rec(self, obstacle_id_with_signal: str) -> None:
        """
        RPi snaps an image and calls the API for image-rec.
        The response is then forwarded back to the android
        :param obstacle_id_with_signal: the current obstacle ID followed by underscore followed by signal
        """
        obstacle_id = obstacle_id_with_signal
        self.logger.info(f"Capturing image for obstacle id: {obstacle_id}")
        # self.android_queue.put(f"info, Capturing image for obstacle id: {obstacle_id}")
        url = f"http://{API_IP}:{API_PORT}/image"
        retry_count = 0

        while True:
            retry_count += 1
            file = Camera().capture_file()

            self.logger.debug("Requesting from image API")

            response = requests.post(
                url,
                files={"file": (file)},
                data={"obstacle_id": obstacle_id},  # Add obstacle_id to the form data
            )

            if response.status_code != 200:
                self.logger.error(
                    "Something went wrong when requesting path from image-rec API. Please try again."
                )
                return

            results = json.loads(response.content)

            if results["image_id"] != "NA" or retry_count > 6:
                break
            elif retry_count > 3:
                self.logger.info(f"Image recognition results: {results}")
            elif retry_count <= 3:
                self.logger.info(f"Image recognition results: {results}")

        # release lock so that bot can continue moving
        try:
            self.movement_lock.release()
            self.retrylock.release()
        except:
            pass

        self.logger.info(f"results: {results}")
        self.logger.info(f"self.obstacles: {self.obstacles}")
        self.logger.info(
            f"Image recognition results: {results} ({results['image_id']})"
        )

        # self.logger.info(
        #     f"Image recognition results: {results} ({SYMBOL_MAP.get(results['image_id'])})"
        # )

        if results["image_id"] == "NA":
            self.failed_obstacles.append(self.obstacles[int(results["obstacle_id"])])
            self.logger.info(
                f"Added Obstacle {results['obstacle_id']} to failed obstacles."
            )
            self.logger.info(f"self.failed_obstacles: {self.failed_obstacles}")
        else:
            self.success_obstacles.append(self.obstacles[int(results["obstacle_id"])])
            self.logger.info(f"self.success_obstacles: {self.success_obstacles}")
        self.android_queue.put(f"TARGET,{results['obstacle_id']},{results['image_id']}")

    # Done
    def request_algo(self, obstacles: list):
        """
        Requests for a series of commands and the path from the Algo API.
        The received commands and path are then queued in the respective queues
        """

        url = f"http://{API_IP}:{API_PORT}/algorithms"

        body = {
            "cat": "obstacles",
            "value": {"obstacles": obstacles, "mode": 0},
            "server_mode": "live",
            "algo_type": "Exhaustive Astar",
        }

        print(body)

        response = requests.post(url, json=body)

        # Error encountered at the server, return early
        if response.status_code != 200:
            # self.android_queue.put(
            #     "error, Something went wrong when requesting path from Algo API."
            # )
            self.logger.error(
                "Something went wrong when requesting path from Algo API."
            )
            return

        result = json.loads(response.content)
        print(result)
        commands = result["commands"]

        # Put commands and paths into respective queues
        self.clear_queues()
        for c in commands:
            self.command_queue.put(c)
        # self.android_queue.put(
        #     "info, Commands and path received Algo API. Robot is ready to move."
        # )
        self.logger.info("Commands and path received Algo API. Robot is ready to move.")

    # Done
    def request_stitch(self):
        """Sends a stitch request to the image recognition API to stitch the different images together"""
        url = f"http://{API_IP}:{API_PORT}/stitch"
        response = requests.post(url)

        # If error, then log, and send error to Android
        if response.status_code != 200:
            # Notify android
            self.android_queue.put(
                "error, Something went wrong when requesting stitch from the API."
            )
            self.logger.error(
                "Something went wrong when requesting stitch from the API."
            )
            return

        self.logger.info("Images stitched!")
        self.android_queue.put("STOP")
        # self.android_queue.put("info, Images stitched!")

    # Done
    def clear_queues(self):
        """Clear both command and path queues"""
        while not self.command_queue.empty():
            self.command_queue.get()

    # Done
    def check_api(self) -> bool:
        """Check whether image recognition and algorithm API server is up and running

        Returns:
            bool: True if running, False if not.
        """
        # Check image recognition API
        url = f"http://{API_IP}:{API_PORT}/status"
        try:
            response = requests.get(url, timeout=1)
            if response.status_code == 200:
                self.logger.debug("API is up!")
                return True
            return False
        # If error, then log, and return False
        except ConnectionError:
            self.logger.warning("API Connection Error")
            return False
        except requests.Timeout:
            self.logger.warning("API Timeout")
            return False
        except Exception as e:
            self.logger.warning(f"API Exception: {e}")
            return False


def main(config):
    print("# ------------- Running Task 1, RPi ---------------- #")
    print(f"You are {'out' if config.is_outdoors else 'in'}doors.")
    task1 = Task1RPI(config)  # init
    task1.start()
