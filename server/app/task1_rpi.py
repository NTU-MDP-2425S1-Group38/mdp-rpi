import json
import os
import time
from multiprocessing import Manager
from threading import Thread
import logging
import requests
import uvicorn
from dotenv import load_dotenv
from modules.serial.android import Android
from modules.serial.stm32 import STM
from modules.web_server.web_server import WebServer
from utils.logger import init_logger
from modules.gamestate import GameState
from multiprocessing import Process

from app_types.obstacle import Obstacle
from app_types.primatives.command import (
    CommandInstruction,
    MoveInstruction,
    TurnInstruction,
)
from app_types.primatives.position import Position
from utils.instructions import Instructions

# # To be explored
# from Communication.pc import PC
# from openapi_client.api.pathfinding_api import PathfindingApi
# from openapi_client.api_client import ApiClient

# # Pathfinding
# from openapi_client.configuration import Configuration
# from openapi_client.models.direction import Direction
# from openapi_client.models.misc_instruction import MiscInstruction
# from openapi_client.models.pathfinding_point import PathfindingPoint
# from openapi_client.models.pathfinding_request import PathfindingRequest
# from openapi_client.models.pathfinding_request_obstacle import (
#     PathfindingRequestObstacle,
# )
# from openapi_client.models.pathfinding_request_robot import PathfindingRequestRobot
# from openapi_client.models.pathfinding_response_move_instruction import (
#     PathfindingResponseMoveInstruction,
# )
# from openapi_client.models.turn_instruction import TurnInstruction
# from TestingScripts.Camera_Streaming_UDP.stream_server import StreamServer

API_IP = "192.168.100.194"
API_PORT = 8000

obstacle_direction = {
    "NORTH": 1,
    "SOUTH": 2,
    "EAST": 3,
    "WEST": 4,
}


class Task1RPI:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("Task1RPI")
        self.gamestate = GameState()
        self.obstacle_dict = {}  # Obstacle Dict
        self.robot = None  # Robot
        self.prev_image = None
        self.stm = STM()
        self.android = Android()
        # self.pc = PC()
        self.manager = Manager()
        self.process_stm_receive = None
        self.process_pc_receive = None
        self.process_pc_stream = None
        self.process_android_receive = None
        self.android_dropped = self.manager.Event()

        # self.conf = Configuration(host="http://192.168.14.13:5001")
        # self.pathfinding_api = PathfindingApi(
        #     api_client=ApiClient(configuration=self.conf)
        # )

        self.last_image = None
        self.prev_image = None
        self.STM_Stopped = False

        self.start_time = 0
        self.drive_speed = 40 if config.is_outdoors else 55
        self.drive_angle = 25

    def request_algo(self, obstacles: list[Obstacle]):
        """
        Requests for a series of commands and the path from the Algo API.
        The received commands and path are then queued in the respective queues
        """

        url = f"http://{API_IP}:{API_PORT}/algo/live"
        converted_obstacles = [
            {"id": o.id, "x": o.position.x, "y": o.position.y, "d": o.direction.value}
            for o in obstacles
        ]
        print("algo")
        body = {
            "cat": "obstacles",
            "value": {"obstacles": converted_obstacles, "mode": 0},
            "server_mode": "live",
            "algo_type": "Exhaustive Astar",
        }

        print(body)

        response = requests.post(url, json=body)

        print("HELLOOO")
        print(response.content)

        # Error encountered at the server, return early
        if response.status_code != 200:
            print("Something went wrong when requesting path from Algo API.")
            return

        return response.content

        # result = json.loads(response.content)["data"]
        # commands = result["commands"]
        # path = result["path"]

        # Log commands received
        # self.logger.debug(f"Commands received from API: {commands}")

        # self.logger.info("Commands and path received Algo API. Robot is ready to move.")

    def initialize(self):
        try:
            # let stream server start before calling other sockets.
            # self.process_pc_stream = Thread(target=self.stream_start)
            # self.process_pc_stream.start()  # Start the Stream
            # time.sleep(0.1)

            self.stm.connect()
            # self.pc.connect()
            self.android.connect()

            print("PC Successfully connected through socket")
            self.process_android_receive = Process(target=self.android_receive)
            self.process_stm_receive = Process(target=self.stm_receive)
            self.process_pc_receive = Process(target=self.run_web_server)

            # Start Threads
            self.logger.info("Starting PC")
            self.process_pc_receive.start()  # Receive from PC
            self.logger.info("Starting android")
            self.process_android_receive.start()  # Receive from android
            self.logger.info("Starting STM")
            self.process_stm_receive.start()  # Receive from stm

        except OSError as e:
            print("Initialization failed: ", e)

    def run_web_server(self) -> None:
        load_dotenv()
        init_logger()
        web_server = WebServer().get_web_server()
        uvicorn.run(
            web_server,
            host="0.0.0.0",
            port=int(os.getenv("WEB_SERVER_PORT", 8080)),  # converts str env var to int
            log_level="debug",
            log_config=None,
        )

    def pc_receive(self) -> None:
        while True:
            try:
                message_rcv = self.pc.receive()
                print(f"Received from PC: {message_rcv}")
                if "NONE" in message_rcv:
                    self.set_last_image("NONE")
                else:
                    msg_split = message_rcv.split(",")
                    if len(msg_split) != 3:
                        continue

                    obstacle_id, conf_str, object_id = msg_split
                    confidence_level = None

                    try:
                        confidence_level = float(conf_str)
                    except ValueError:
                        confidence_level = None

                    print("OBJECT ID:", object_id)

                    if confidence_level is not None:
                        self.android.send(f"TARGET,{obstacle_id},{object_id}")

            except OSError as e:
                print(f"Error in receiving data: {e}")
                break

    # Done (Android)
    def android_receive(self) -> None:
        print("Went into android receive function")
        while True:
            message_rcv = None
            try:
                message_rcv = self.android.receive()
                messages = message_rcv.split("\n")
                for message_rcv in messages:
                    if len(message_rcv) == 0:
                        continue

                    print("Message received from Android:", message_rcv)
                    if "BEGIN" in message_rcv:
                        print("BEGINNNN!")
                        # TODO: Begin Task 1
                        self.start()  # Calculate the path
                    elif "CLEAR" in message_rcv:
                        print(
                            " --------------- CLEARING OBSTACLES LIST. ---------------- "
                        )
                        self.obstacle_dict.clear()
                    elif "OBSTACLE" in message_rcv:
                        print("OBSTACLE!!!!")
                        id, x, y, dir = message_rcv.split(",")[1:]
                        id = int(id)

                        if dir == "-1":
                            if id in self.obstacle_dict:
                                del self.obstacle_dict[id]
                                print("Deleted obstacle", id)
                        elif dir not in ["NORTH", "SOUTH", "EAST", "WEST"]:
                            print("Invalid direction provided:", dir + ", ignoring...")
                            continue
                        else:
                            newObstacle = Obstacle(
                                id=id,
                                position=Position(x=int(x), y=int(y)),
                                direction=obstacle_direction[dir],
                            )
                            self.obstacle_dict[id] = newObstacle

                            print("Obstacle set successfully: ", newObstacle)
                        print(
                            f"--------------- Current list {len(self.obstacle_dict)}: -------------"
                        )
                        obs_items = self.obstacle_dict.items()
                        if len(obs_items) == 0:
                            print("! no obstacles.")
                        else:
                            for id, obstacle in obs_items:
                                print(f"{id}: {obstacle}")

                    elif "ROBOT" in message_rcv:
                        print("NEW ROBOT LOCATION!!!")
                        x, y, dir = message_rcv.split(",")[1:]
                        x, y = int(x), int(y)

                        if x < 0 or y < 0:
                            print("Illegal robot coordinate, ignoring...")
                            continue

                        self.robot = {"x": x, "y": y, "dir": dir}
                        print("Robot set successfully: ", self.robot)
                    else:
                        # Catch for messages with no keywords (OBSTACLE/ROBOT/BEGIN)
                        print("Not a keyword, message received: ", message_rcv)

            except OSError:
                self.android_dropped.set()
                print("Event set: Bluetooth connection dropped")

            if message_rcv is None:
                continue

    # Done (STM)
    def stm_receive(self) -> None:
        msg = ""
        while True:
            message_rcv = None
            try:
                message_rcv = self.stm.wait_receive()
                print("Message received from STM: ", message_rcv)
                if "fS" in message_rcv:
                    self.set_stm_stop(
                        True
                    )  # Finished stopping, can start delay to recognise image
                    self.gamestate.capture_and_process_image()
                    print("Setting STM Stopped to true")
                elif message_rcv[0] == "f":
                    # Finished command, send to android
                    message_split = message_rcv[1:].split(
                        "|"
                    )  # Ignore the 'f' at the start
                    cmd_speed = message_split[0]
                    turning_degree = message_split[1]
                    distance = message_split[2].strip()

                    cmd = cmd_speed[0]  # Command (t/T)

                    if turning_degree == f"-{self.drive_angle}":
                        # Turn left
                        if cmd == "t":
                            # Backward left
                            msg = "TURN,BACKWARD_LEFT,0"
                        elif cmd == "T":
                            # Forward left
                            msg = "TURN,FORWARD_LEFT,0"
                    elif turning_degree == f"{self.drive_angle}":
                        # Turn right
                        if cmd == "t":
                            # Backward right
                            msg = "TURN,BACKWARD_RIGHT,0"
                        elif cmd == "T":
                            # Forward right
                            msg = "TURN,FORWARD_RIGHT,0"
                    elif turning_degree == "0":
                        if cmd == "t":
                            # Backward
                            msg = "MOVE,BACKWARD," + distance
                        elif cmd == "T":
                            # Forward
                            msg = "MOVE,FORWARD," + distance
                    else:
                        # Unknown turning degree
                        print("Unknown turning degree")
                        msg = "No instruction"
                        continue

                    print("Msg: ", msg)
                    try:
                        self.android.send(msg)
                        print("SENT TO ANDROID SUCCESSFULLY: ", msg)
                    except OSError:
                        self.android_dropped.set()
                        print("Event set: Android dropped")

                    self.android_dropped.clear()  # Clear previously set event

            except OSError as e:
                print(f"Error in receiving STM data: {e}")

            if message_rcv is None:
                continue

    # Done (Gamestate)
    def stop(self):
        """Stops all processes on the RPi and disconnects from Android, STM and PC"""
        time.sleep(0.2)
        self.android.send("STOP")
        # self.android.disconnect()
        # self.stm.disconnect()
        # self.pc.disconnect()
        # TODO: Add Stream disconnect/end
        print("Program Ended\n")

    # Done (Gamestate)
    def start(self):
        # pathfindingRequest = PathfindingRequest(
        #     obstacles=self.obstacle_dict.values(), robot=self.robot, verbose=False
        # )
        obstacles = list(self.obstacle_dict.values())
        # response: Instructions = None

        self.start_time = time.time_ns()
        print("! Sending request to API...")
        commands = json.loads(self.request_algo(obstacles))["commands"]
        # try:
        #     # response = self.pathfinding_api.pathfinding_post(pathfindingRequest)
        #     response = self.gamestate.set_obstacles(obstacles)
        # except:
        #     print("Server failed, try again.")
        #     return

        print(
            f"! Request completed in {(time.time_ns() - self.start_time) / 1e9:.3f}s."
        )
        count = 0
        while len(commands) > 0:
            cmd = commands.pop(0)
            self.logger.info(f"Current command: {cmd}")
            angle = 0
            flag = ""
            val = 0

            print(cmd)

            if isinstance(cmd["value"], dict) and cmd["value"]["move"] in [
                "FORWARD",
                "BACKWARD",
            ]:
                move_direction = cmd["value"]["move"]
                angle = 0
                val = cmd["value"]["amount"]
                self.logger.info(f"AMOUNT TO MOVE: {val}")
                self.logger.info(f"MOVE DIRECTION: {move_direction}")

                if move_direction == "FORWARD":
                    flag = "T"
                elif move_direction == "BACKWARD":
                    flag = "t"
            else:
                if cmd["value"] == "CAPTURE_IMAGE":
                    flag = "S"
                    count += 1
                    self.stm.send_cmd(flag, int(self.drive_speed), int(angle), int(val))
                    # self.stop_and_snap(cmd)
                    continue

                elif cmd["value"] in [
                    "FORWARD_LEFT",
                    "FORWARD_RIGHT",
                    "BACKWARD_LEFT",
                    "BACKWARD_RIGHT",
                ]:
                    val = 90
                    if cmd["value"] == "FORWARD_LEFT":
                        flag = "T"
                        angle = -self.drive_angle
                    elif cmd["value"] == "FORWARD_RIGHT":
                        flag = "T"
                        angle = self.drive_angle
                    elif cmd["value"] == "BACKWARD_LEFT":
                        flag = "t"
                        angle = -self.drive_angle
                    elif cmd["value"] == "BACKWARD_RIGHT":
                        flag = "t"
                        angle = self.drive_angle

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
                # if len(self.failed_obstacles) != 0 and self.failed_attempt is False:
                #     new_obstacle_list = list(self.failed_obstacles)
                #     for i in list(self.success_obstacles):
                #         # {'x': 5, 'y': 11, 'id': 1, 'd': 4}
                #         i["d"] = 8
                #         new_obstacle_list.append(i)

                #     self.logger.info("Attempting to go to failed obstacles")
                #     self.failed_attempt = True
                #     self.request_algo(new_obstacle_list)
                #     self.retrylock = self.manager.Lock()
                #     self.movement_lock.release()
                #     continue

                self.unpause.clear()
                self.movement_lock.release()
                self.logger.info("Commands queue finished.")
                self.android_queue.put("info, Commands queue finished.")
                self.android_queue.put("status, finished")
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
        self.android_queue.put(f"info, Capturing image for obstacle id: {obstacle_id}")
        url = f"http://{API_IP}:{API_PORT}/image"
        filename = f"{int(time.time())}_{obstacle_id}.jpg"

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
        self.movement_lock.release()
        try:
            self.retrylock.release()
        except:
            pass

        self.logger.info(f"results: {results}")
        self.logger.info(f"self.obstacles: {self.obstacles}")
        self.logger.info(
            f"Image recognition results: {results} ({SYMBOL_MAP.get(results['image_id'])})"
        )

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
            self.android_queue.put(
                "error, Something went wrong when requesting path from Algo API."
            )
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
        self.android_queue.put(
            "info, Commands and path received Algo API. Robot is ready to move."
        )
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
        self.android_queue.put("info, Images stitched!")

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
    task1.initialize()
