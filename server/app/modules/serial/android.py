import json
import os
import socket
import sys
import time
from pathlib import Path
from typing import Optional

import bluetooth

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


# class AndroidDummy:
#     def connect(self):
#         print("Connected to Android dummy.")

#     def disconnect(self):
#         print("Disconnected from Android dummy.")

#     def send(self, message):
#         print(f"Sent {message} to Android dummy.")

#     def receive(self):
#         while True:
#             pass


class Android(Link):
    def __init__(self):
        """
        Initialize the Bluetooth connection.
        """
        # Initialize super class's init.
        super().__init__()
        self.hostId = "192.168.14.14"
        # UUID to be generated, but can just use the default one - Bryan
        self.uuid = (
            "00001101-0000-1000-8000-00805f9b34fb"  # Default but should try generated
        )
        self.connected = False
        self.client_socket = None
        self.server_socket = None

    def connect(self):
        """
        Connect to Andriod by Bluetooth
        """
        print("Bluetooth Connection Started")
        try:
            # Make RPi discoverable by the Android tablet to complete pairing
            os.system("sudo hciconfig hci0 piscan")

            # Initialize server socket
            self.server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self.server_sock.bind(("", bluetooth.PORT_ANY))
            self.server_sock.listen(1)

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

            print("Awaiting bluetooth connection on port: %d", port)
            self.client_socket, client_address = self.server_socket.accept()
            print("Accepted connection from client address of: %s", str(client_address))
            self.connected = True

        except Exception as e:
            # Prints out the error if socket connection failed.
            print("Android socket connection failed: %s", str(e))
            self.server_socket.close()
            self.client_socket.close()

    def disconnect(self):
        """Disconnect from Android Bluetooth connection and shutdown all the sockets established"""
        try:
            print("Disconnecting bluetooth")
            # socket.shutdown is not necessary to close the connection, but is beneficial when dealing with multithreading processes. - Bryan
            self.server_socket.shutdown(socket.SHUT_RDWR)
            self.client_socket.shutdown(socket.SHUT_RDWR)
            self.client_socket.close()
            self.server_socket.close()
            self.client_socket = None
            self.server_socket = None
            self.connected = False
            time.sleep(1)  # Time for cleanup
            print("Bluetooth has been disconnected")
        except Exception as e:
            print("Failed to disconnect bluetooth: %s", str(e))

    def send(self, message: AndroidMessage):
        """Send message to Android"""
        try:
            # Default code to send a message to Android. - Bryan
            # ~ self.client_socket.send(f"{message.jsonify}\n".encode("utf-8"))
            self.client_socket.send(f"{message}\n".encode("utf-8"))
            print("Sent to Android: %s", str(message))
            # ~ print("Sent to Android: %s", str(message.jsonify))
        except OSError as e:
            print("Message sending failed: %s", str(e))
            raise e

    def receive(self) -> Optional[str]:
        """Receive message from Android"""
        try:
            # ~ while True:
            # Default code to receive data from Android in JSON format. - Bryan
            unclean_message = self.client_socket.recv(1024)
            message = unclean_message.strip().decode("utf-8")
            # ~ print("Message received from Android: %s", str(message))
            # ~ response_data = "Message received successfully!"
            # ~ self.client_socket.send(response_data.encode('utf-8'))
            # ~ print(message)
            return message
        except OSError as e:  # connection broken, try to reconnect
            print("Message failed to be received: %s", str(e))
            raise e
