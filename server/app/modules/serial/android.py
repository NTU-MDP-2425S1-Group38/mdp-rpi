import json
import logging
import os
import socket
import sys
import time
from pathlib import Path
from typing import Optional

import bluetooth

from modules.gamestate.gamestate import GameState
from modules.serial.stm32 import STM

from utils.metaclass.singleton import Singleton
from app_types.obstacle import Obstacle
from app_types.primatives.position import Position

from .link import Link


class AndroidMessage:
    """
    Class for communicating with Android tablet over Bluetooth.
    """

    def __init__(self, cat: str, value: str):
        """
        Constructor for AndroidMessage.
        :param cat: Message category.
        :param value: Message value.
        """
        self._cat = cat
        self._value = value

    def __str__(self):
        return self._value

    @property
    def cat(self):
        """
        Returns the message category.
        :return: String representation of the message category.
        """
        return self._cat

    @property
    def value(self):
        """
        Returns the message as a string.
        :return: String representation of the message.
        """
        return self._value

    @property
    def jsonify(self) -> str:
        """
        Returns the message as a JSON string.
        :return: JSON string representation of the message.
        """
        return json.dumps({"type": self._type, "value": self._value})


class Android(metaclass=Singleton):
    gamestate: GameState
    stm: STM

    def __init__(self):
        """
        Initialize the Bluetooth connection.
        """
        # UUID to be generated, but can just use the default one - Bryan
        self.uuid = (
            "00001101-0000-1000-8000-00805f9b34fb"  # Default but should try generated
        )
        self.connected = False
        self.client_socket = None
        self.server_socket = None
        self.logger = logging.getLogger()
        self.obstacle_dict: dict[str, Obstacle] = {}

    def connect(self):
        """
        Connect to Andriod by Bluetooth
        """
        print("Bluetooth Connection Started")
        try:
            # Make RPi discoverable by the Android tablet to complete pairing
            os.system("sudo hciconfig hci0 piscan")

            # Initialize server socket
            self.server_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self.server_socket.bind(("", bluetooth.PORT_ANY))
            self.server_socket.listen(1)

            # Parameters
            port = self.server_socket.getsockname()[1]
            uuid = "94f39d29-7d6d-437d-973b-fba39e49d4ee"

            # Advertise
            bluetooth.advertise_service(
                self.server_socket,
                "MDP-Group38-RPi",
                service_id=uuid,
                service_classes=[uuid, bluetooth.SERIAL_PORT_CLASS],
                profiles=[bluetooth.SERIAL_PORT_PROFILE],
            )

            self.logger.info(f"Awaiting bluetooth connection on port: {port}")
            self.client_socket, client_address = self.server_socket.accept()
            self.logger.info(
                f"Accepted connection from client address of: {str(client_address)}"
            )
            self.connected = True

        except Exception as e:
            # Prints out the error if socket connection failed.
            self.logger.info("Android socket connection failed: %s", str(e))
            self.server_socket.close()
            self.client_socket.close()

    def disconnect(self):
        """Disconnect from Android Bluetooth connection and shutdown all the sockets established"""
        try:
            self.logger.info("Disconnecting bluetooth")
            # socket.shutdown is not necessary to close the connection, but is beneficial when dealing with
            # multithreading processes. - Bryan
            self.server_socket.shutdown(socket.SHUT_RDWR)
            self.client_socket.shutdown(socket.SHUT_RDWR)
            self.client_socket.close()
            self.server_socket.close()
            self.client_socket = None
            self.server_socket = None
            self.connected = False
            time.sleep(1)  # Time for cleanup
            self.logger.info("Bluetooth has been disconnected")
        except Exception as e:
            self.logger.error(f"Failed to disconnect bluetooth: {str(e)}")

    def send(self, message: AndroidMessage):
        """Send message to Android"""
        try:
            # Default code to send a message to Android. - Bryan
            # ~ self.client_socket.send(f"{message.jsonify}\n".encode("utf-8"))
            self.client_socket.send(f"{message}\n".encode("utf-8"))
            self.logger.info("Sent to Android: %s", str(message))
            # ~ self.logger.info("Sent to Android: %s", str(message.jsonify))
        except OSError as e:
            self.logger.info("Message sending failed: %s", str(e))
            raise e

    def receive(self) -> Optional[str]:
        """Receive message from Android"""
        try:
            # ~ while True:
            # Default code to receive data from Android in JSON format. - Bryan
            unclean_message = self.client_socket.recv(1024)
            message = unclean_message.strip().decode("utf-8")
            # ~ self.logger.info("Message received from Android: %s", str(message))
            # ~ response_data = "Message received successfully!"
            # ~ self.client_socket.send(response_data.encode('utf-8'))
            # ~ self.logger.info(message)
            return message
        except OSError as e:  # connection broken, try to reconnect
            self.logger.error(f"Message failed to be received: {str(e)}")
            raise e

    def run(self) -> None:
        """
        Main running function in a while loop
        :return:
        """

        self.connect()
        self.logger.info("Went into android receive function")

        ### TESTING
        # Currently reflect sent message back to the tablet

        while True:
            message_rcv = None
            try:
                message_rcv = self.receive()
                flag, drive_speed, angle, val = message_rcv.split(",")
                self.stm.send_cmd(flag, drive_speed, angle, val)
            except OSError:
                # self.android_dropped.set()
                self.logger.info("Event set: Bluetooth connection dropped")

        # Task 1
        # while True:
        #     message_rcv = None
        #     try:
        #         message_rcv = self.receive()
        #         messages = message_rcv.split("\n")
        #         for message_rcv in messages:
        #             if len(message_rcv) == 0:
        #                 continue

        #             self.logger.info("Message received from Android: %s", message_rcv)
        #             if "BEGIN" in message_rcv:
        #                 self.logger.info("BEGINNNN!")
        #                 # TODO: Begin Task 1
        #                 obstacles = list(self.obstacle_dict.values())
        #                 self.gamestate.set_obstacles(obstacles)
        #             elif "CLEAR" in message_rcv:
        #                 print(
        #                     " --------------- CLEARING OBSTACLES LIST. ---------------- "
        #                 )
        #                 self.obstacle_dict.clear()
        #             elif "OBSTACLE" in message_rcv:
        #                 print("OBSTACLE!!!!")
        #                 x, y, dir, id = message_rcv.split(",")[1:]

        #                 id = int(id)

        #                 if dir == "-1":
        #                     if id in self.obstacle_dict:
        #                         del self.obstacle_dict[id]
        #                         print("Deleted obstacle", id)
        #                 elif dir not in ["N", "S", "E", "W"]:
        #                     print("Invalid direction provided:", dir + ", ignoring...")
        #                     continue
        #                 else:
        #                     newObstacle = Obstacle(
        #                         id=id,
        #                         position=Position(int(x), int(y)),
        #                         direction=dir,
        #                     )
        #                     self.obstacle_dict[id] = newObstacle

        #                     print("Obstacle set successfully: ", newObstacle)
        #                 print(
        #                     f"--------------- Current list {len(self.obstacle_dict)}: -------------"
        #                 )
        #                 obs_items = self.obstacle_dict.items()
        #                 if len(obs_items) == 0:
        #                     print("! no obstacles.")
        #                 else:
        #                     for id, obstacle in obs_items:
        #                         print(f"{id}: {obstacle}")

        #             elif "ROBOT" in message_rcv:
        #                 print("NEW ROBOT LOCATION!!!")
        #                 x, y, dir = message_rcv.split(",")[1:]
        #                 x, y = int(x), int(y)

        #                 if x < 0 or y < 0:
        #                     print("Illegal robot coordinate, ignoring...")
        #                     continue

        #                 self.robot = {"x": x, "y": y, "dir": dir}
        #                 print("Robot set successfully: ", json.dumps(self.robot))
        #             else:
        #                 # Catch for messages with no keywords (OBSTACLE/ROBOT/BEGIN)
        #                 print("Not a keyword, message received: ", message_rcv)

        #     except OSError:
        #         # self.android_dropped.set()
        #         print("Event set: Bluetooth connection dropped")

        #     if message_rcv is None:
        #         continue
