"""
Entry file to start the server on the Raspberry Pi.
"""
import logging
import os
from multiprocessing import Process
from dotenv import load_dotenv

from modules.camera.camera import Camera
from modules.web_server.web_server import WebServer
from modules.serial.stm32 import STM
from modules.serial.android import Android
from utils.logger import init_logger
import uvicorn


def run_web_server() -> None:
    load_dotenv()
    init_logger()
    logging.getLogger().info("Starting server as main!")
    web_server = WebServer().get_web_server()
    uvicorn.run(
        web_server,
        host="0.0.0.0",
        port=int(os.getenv("WEB_SERVER_PORT", 8080)),  # converts str env var to int
        log_level="debug",
        log_config=None,
    )


def run_bluetooth_server() -> None:
    load_dotenv()
    init_logger()
    android = Android()
    android.run()


def run_stm():
    load_dotenv()
    init_logger()
    # stm = STM()
    # stm.connect()


def main():
    load_dotenv()
    init_logger()

    server_process = Process(target=run_web_server)
    bluetooth_process = Process(target=run_bluetooth_server)
    stm_process = Process(target=run_stm)

    bluetooth_process.start()
    server_process.start()
    stm_process.start()

    bluetooth_process.join()
    server_process.join()
    stm_process.join()

    # drive_speed = 40
    # drive_angle = 25

    # stm = STM()

    # stm.connect()

    # Forward
    # stm.send_cmd("T", drive_speed, 0, 30)
    # print("Forward")

    # Backward
    # stm.send_cmd("t", drive_speed, 0, 30)
    # print("Backward")

    # Forward Left
    # stm.send_cmd("T", drive_speed, -drive_angle, 90)
    # print("Forward Left")

    # Forward Right
    # stm.send_cmd("T", drive_speed, drive_angle, 90)
    # print("Forward Right")

    # Backward Left
    # stm.send_cmd("t", drive_speed, -drive_angle,90)
    # print("Backward Left")

    # Backward Right
    # stm.send_cmd("t", drive_speed, drive_angle, 90)
    # print("Backward Right")

# def stm_receive(self) -> None:
#     msg = ""
#     while True:
#         message_rcv = None
#         try:
#             message_rcv = self.stm.wait_receive()
#             print("Message received from STM: ", message_rcv)
#             if "fS" in message_rcv:
#                 self.set_stm_stop(
#                     True
#                 )  # Finished stopping, can start delay to recognise image
#                 print("Setting STM Stopped to true")
#             elif message_rcv[0] == "f":
#                 # Finished command, send to android
#                 message_split = message_rcv[1:].split(
#                     "|"
#                 )  # Ignore the 'f' at the start
#                 cmd_speed = message_split[0]
#                 turning_degree = message_split[1]
#                 distance = message_split[2].strip()
#
#                 cmd = cmd_speed[0]  # Command (t/T)
#                 speed = cmd_speed[1:]
#
#                 send_count = 1
#
#                 if turning_degree == f"-{self.drive_angle}":
#                     # Turn left
#                     if cmd == "t":
#                         # Backward left
#                         msg = "TURN,BACKWARD_LEFT,0"
#                     elif cmd == "T":
#                         # Forward left
#                         msg = "TURN,FORWARD_LEFT,0"
#                 elif turning_degree == f"{self.drive_angle}":
#                     # Turn right
#                     if cmd == "t":
#                         # Backward right
#                         msg = "TURN,BACKWARD_RIGHT,0"
#                     elif cmd == "T":
#                         # Forward right
#                         msg = "TURN,FORWARD_RIGHT,0"
#                 elif turning_degree == "0":
#                     if cmd == "t":
#                         # Backward
#                         msg = "MOVE,BACKWARD," + distance
#                     elif cmd == "T":
#                         # Forward
#                         msg = "MOVE,FORWARD," + distance
#                 else:
#                     # Unknown turning degree
#                     print("Unknown turning degree")
#                     msg = "No instruction"
#                     continue
#
#                 print("Msg: ", msg)
#                 try:
#                     self.android.send(msg)
#                     print("SENT TO ANDROID SUCCESSFULLY: ", msg)
#                 except OSError:
#                     self.android_dropped.set()
#                     print("Event set: Android dropped")
#
#                 self.android_dropped.clear()  # Clear previously set event
#
#         except OSError as e:
#             print(f"Error in receiving STM data: {e}")
#
#         if message_rcv is None:
#             continue


if __name__ == "__main__":
    main()
