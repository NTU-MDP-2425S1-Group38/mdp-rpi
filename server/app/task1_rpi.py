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
            self.process_android_receive = Thread(target=self.android_receive)
            self.process_stm_receive = Thread(target=self.stm_receive)
            # self.process_pc_receive = Thread(target=self.pc_receive)

            # Start Threads
            # self.process_pc_receive.start()  # Receive from PC
            self.process_android_receive.start()  # Receive from android
            self.process_stm_receive.start()  # Receive from stm

        except OSError as e:
            print("Initialization failed: ", e)

    def run_web_server(ready_event) -> None:
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
        ready_event.set()  # Signal that the web server is ready

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
        while cmd := commands.pop():
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
                        angle = -self.drive_angle
                    elif cmd.value == "FORWARD_RIGHT":
                        flag = "T"
                        angle = self.drive_angle
                    elif cmd.value == "BACKWARD_LEFT":
                        flag = "t"
                        angle = -self.drive_angle

            self.stm.send_cmd(flag, self.drive_speed, angle, val)
            print("STM Command sent successfully...")
            while not self.get_stm_stop():
                # Wait until the STM has execute all the commands and stopped (True), then wait x seconds to recognise image
                pass

            time.sleep(0.75)
            print("STM stopped, sending time of capture...")
            self.pc.send(f"DETECT,{cmd.capture_id}")

        # Original code
        # for i, segment in enumerate(segments):
        #     print(f"On segment {i+1} of {len(segments)}:")
        #     self.set_stm_stop(False)  # Reset to false upon starting the new segment

        #     print("SEGMENT NUMBER ", i)
        #     i = i + 1

        #     for instruction in segment.instructions:
        #         actual_instance = instruction.actual_instance
        #         inst = ""
        #         flag = ""
        #         angle = 0
        #         val = 0

        #         if hasattr(actual_instance, "move"):  # MOVE Instruction
        #             inst = PathfindingResponseMoveInstruction(
        #                 amount=actual_instance.amount, move=actual_instance.move
        #             )
        #             move_direction = inst.move.value
        #             angle = 0
        #             val = inst.amount
        #             print("AMOUNT TO MOVE: ", val)
        #             print("MOVE DIRECTION: ", move_direction)

        #             # Send instructions to stm
        #             if move_direction == "FORWARD":
        #                 flag = "T"
        #             elif move_direction == "BACKWARD":
        #                 flag = "t"

        #         else:
        #             try:
        #                 inst = TurnInstruction(actual_instance)  # TURN Instruction
        #             except:
        #                 inst = MiscInstruction(actual_instance)  # MISC Instruction

        #             # print("Final Instruction ", inst)
        #             if (
        #                 isinstance(inst, MiscInstruction)
        #                 and str(inst.value) == "CAPTURE_IMAGE"
        #             ):
        #                 flag = "S"  # STM to stop before recognising image and sending results to RPi

        #             elif isinstance(inst, TurnInstruction):
        #                 val = 90
        #                 if inst.value == "FORWARD_LEFT":
        #                     flag = "T"
        #                     angle = -self.drive_angle
        #                 elif inst.value == "FORWARD_RIGHT":
        #                     flag = "T"
        #                     angle = self.drive_angle
        #                 elif inst.value == "BACKWARD_LEFT":
        #                     flag = "t"
        #                     angle = -self.drive_angle
        #                 else:
        #                     # BACKWARD_RIGHT
        #                     flag = "t"
        #                     angle = self.drive_angle

        #         self.stm.send_cmd(flag, self.drive_speed, angle, val)
        #     print("STM Command sent successfully...")
        #     while not self.get_stm_stop():
        #         # Wait until the STM has execute all the commands and stopped (True), then wait x seconds to recognise image
        #         pass

        #     time.sleep(0.75)
        #     print("STM stopped, sending time of capture...")
        #     self.pc.send(f"DETECT,{segment.image_id}")

        print(
            f">>>>>>>>>>>> Completed in {(time.time_ns() - self.start_time) / 1e9:.2f} seconds."
        )
        try:
            print("request stitch")
            self.pc.send(f"PERFORM STITCHING,{len(count)}")
        except OSError as e:
            print("Error in sending stitching command to PC: " + e)

        self.stop()

    def set_last_image(self, img) -> None:
        print(f"Setting last_image as {self.last_image}")
        self.last_image = img

    def set_stm_stop(self, val) -> None:
        self.STM_Stopped = val

    def get_stm_stop(self) -> bool:
        return self.STM_Stopped


def main(config):
    print("# ------------- Running Task 1, RPi ---------------- #")
    print(f"You are {'out' if config.is_outdoors else 'in'}doors.")
    task1 = Task1RPI(config)  # init
    task1.initialize()
