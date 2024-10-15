import logging

from utils.metaclass.singleton import Singleton
from .configuration import BAUD_RATE, SERIAL_PORT
from pathlib import Path
from typing import Optional, List

# from modules.gamestate import GameState
import time

# from modules.serial.android import Android

import serial

from .stm_commands import StmCommand


class STM(metaclass=Singleton):
    def __init__(self):
        """
        Constructor for STMLink.
        """
        self.serial_link = None
        self.received = []
        self.logger = logging.getLogger("STM")

    def connect(self):
        """Connect to STM32 using serial UART connection, given the serial port and the baud rate"""
        self.serial_link = serial.Serial(SERIAL_PORT, BAUD_RATE)
        print("Connected to STM32")

    def disconnect(self):
        """Disconnect from STM32 by closing the serial link that was opened during connect()"""
        self.serial_link.close()
        self.serial_link = None
        print("Disconnected from STM32")

    def send(self, message: str) -> None:
        """Send a message to STM32, utf-8 encoded

        Args:
            message (str): message to send
        """
        self.serial_link.write(bytes(message, "utf-8"))
        self.logger.info(f"Sent to STM32: {str(message).rstrip()}")

    def send_stm_command(self, *stm_commands:StmCommand) -> None:
        """
        Function to take StmCommand super classes
        :param stm_commands: Commands to be sent to the STM
        :return:
        """
        for c in stm_commands:
            self.send(c.to_serial())

    def send_stm_command_and_wait(self, *stm_commands:StmCommand) -> None:
        """
        A more "sync" version of send_stm_command
        :param stm_commands:
        :return:
        """

        for c in stm_commands:
            self.send(c.to_serial())
            self.wait_receive()

    def send_cmd(self, flag, speed, angle, val):
        """Send command and wait for acknowledge."""
        cmd = flag
        if flag not in ["S", "D", "M"]:
            cmd += f"{speed}|{round(angle, 2)}|{round(val, 2)}"
        cmd += "\n"
        self.send(cmd)

    def wait_receive(self, ticks=5000) -> Optional[str]:
        """Receive a message from STM32, utf-8 decoded

        Returns:
            Optional[str]: message received
        """
        while True:
            if self.serial_link.in_waiting > 0:
                payload = str(self.serial_link.read_all(), "utf-8")
                self.logger.info(f"Received: {payload}")
                return payload

    def run_task_1(self):
        """Run the STM32 module."""
        self.connect()
        msg = ""

        while True:
            message_rcv = None
            try:
                message_rcv = self.wait_receive()
                self.gamestate
                print("Message received from STM: ", message_rcv)
                if "fS" in message_rcv:
                    self.gamestate.set_stm_stop(
                        True
                    )  # Finished stopping, can start delay to recognise image
                    print("Setting STM Stopped to true")
                if message_rcv[0] == "f":
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

    def run_task_2(self):
        """Run the STM32 module."""
        self.connect()

        while True:
            try:
                messages = self.stm.wait_receive()
                print(f"all messages: {messages}")
                for message_rcv in messages.split("\n"):
                    if len(message_rcv) == 0:
                        continue
                    print("Message received from STM: ", message_rcv)
                    if "M" in message_rcv:
                        if self.gamestate.num_M == 0:
                            time.sleep(0.25)
                            self.pc.send("SEEN")
                        elif self.gamestate.num_M == 1:
                            self.gamestate.stop()

                        self.num_M += 1
                    elif "D" in message_rcv:
                        dist_val_str = (
                            message_rcv.replace("fD", "").replace("\0", "").strip()
                        )
                        if len(dist_val_str) == 0:
                            # Robot is beginning drive towards obstacle, take in latest_image then decide what to do
                            if self.gamestate.num_obstacle == 1:  # First Obstacle
                                if (
                                    self.gamestate.get_last_image()
                                    == self.gamestate.RIGHT_ARROW_ID
                                ):  # RIGHT ARROW
                                    print("Right arrow detected")
                                    self.gamestate.callback_obstacle1(True)

                                elif (
                                    self.gamestate.get_last_image()
                                    == self.gamestate.LEFT_ARROW_ID
                                ):  # LEFT ARROW
                                    print("Left arrow detected")
                                    self.gamestate.callback_obstacle1(False)

                                else:
                                    # set to trigger on next arrow found.
                                    self.gamestate.on_arrow_callback = (
                                        self.gamestate.callback_obstacle1
                                    )

                            elif self.gamestate.num_obstacle == 2:  # Second Obstacle
                                if (
                                    self.gamestate.get_last_image()
                                    == self.gamestate.RIGHT_ARROW_ID
                                ):  # RIGHT ARROW
                                    print("Right arrow detected")
                                    self.gamestate.callback_obstacle2(True)

                                elif (
                                    self.gamestate.get_last_image()
                                    == self.gamestate.LEFT_ARROW_ID
                                ):  # LEFT ARROW
                                    print("Left arrow detected")
                                    self.gamestate.callback_obstacle2(False)

                                else:
                                    # set to trigger on next arrow found.
                                    self.gamestate.on_arrow_callback = (
                                        self.gamestate.callback_obstacle2
                                    )

                            self.gamestate.num_obstacle += 1
                        else:
                            # Robot has finished tracking distance; save accordingly
                            dist_val = float(dist_val_str)

                            # set distances in order.
                            with self.gamestate.lock:
                                if self.gamestate.obstacle_dist1 is None:
                                    self.gamestate.obstacle_dist1 = dist_val
                                elif self.gamestate.obstacle_dist2 is None:
                                    self.gamestate.obstacle_dist2 = dist_val
                                elif self.gamestate.wall_dist is None:
                                    self.gamestate.wall_dist = dist_val + 22.5
                                    self.gamestate.wall_complete = True

            except OSError as e:
                print(f"Error in receiving STM data: {e}")
