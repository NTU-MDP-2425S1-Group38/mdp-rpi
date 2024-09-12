from utils.metaclass.singleton import Singleton
from .configuration import BAUD_RATE, SERIAL_PORT
from pathlib import Path
from typing import Optional

import serial


class STM(metaclass=Singleton):
    def __init__(self):
        """
        Constructor for STMLink.
        """
        self.serial_link = None
        self.received = []

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
        print("Sent to STM32:", str(message).rstrip())

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
                return str(self.serial.read_all(), "utf-8")

    def run(self):
        """Run the STM32 module."""
        self.connect()
        msg = ""

        while True:
            message_rcv = None

            try:
                message_rcv = self.wait_receive()
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
                    speed = cmd_speed[1:]

                    send_count = 1

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
