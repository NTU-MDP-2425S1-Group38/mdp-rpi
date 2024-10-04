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
SYMBOL_MAP = {"RIGHT": "38", "LEFT": 39}


class PiAction:
    def __init__(self, cat, value):
        self._cat = cat
        self._value = value

    @property
    def cat(self):
        return self._cat

    @property
    def value(self):
        return self._value


class RaspberryPi:
    def __init__(self):
        # Initialize logger and communication objects with Android and STM
        self.logger = prepare_logger()
        self.android = Android()
        self.stm = STM()

        # For sharing information between child processes
        self.manager = Manager()

        # Set robot mode to be 1 (Path mode)
        self.robot_mode = self.manager.Value("i", 1)

        # Events
        self.android_dropped = self.manager.Event()  # Set when the android link drops
        # commands will be retrieved from commands queue when this event is set
        self.unpause = self.manager.Event()

        # Movement Lock
        self.movement_lock = self.manager.Lock()

        # Queues
        self.android_queue = self.manager.Queue()  # Messages to send to Android
        self.rpi_action_queue = (
            self.manager.Queue()
        )  # Messages that need to be processed by RPi
        self.command_queue = (
            self.manager.Queue()
        )  # Messages that need to be processed by STM32, as well as snap commands

        # Define empty processes
        self.proc_recv_android = None
        self.proc_recv_stm32 = None
        self.proc_android_sender = None
        self.proc_command_follower = None
        self.proc_rpi_action = None

        self.ack_count = 0
        self.near_flag = self.manager.Lock()

        self.capture_dist1 = 30  # distance between first arrow and where car will stop.
        self.capture_dist2 = (
            20  # distance between second arrow and where car will stop.
        )

    # Done
    def start(self):
        """Starts the RPi orchestrator"""
        try:
            # Establish Bluetooth connection with Android
            self.android.connect()
            self.android_queue.put("info, You are connected to the RPi!")

            # Establish connection with STM32
            self.stm.connect()

            # Check Image Recognition and Algorithm API status
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
            self.android_queue.put("mode, manual")

            # Handover control to the Reconnect Handler to watch over Android connection
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
            self.android_queue.put("info, You are reconnected!")
            self.android_queue.put("mode, manual")

            self.android_dropped.clear()

    def recv_android(self) -> None:
        """
        [Child Process] Processes the messages received from Android
        """

        while True:
            msg_str: Optional[str] = None
            try:
                msg_str = self.android.recv()
            except OSError:
                self.android_dropped.set()
                self.logger.debug("Event set: Android connection dropped")

            # If an error occurred in recv()
            if msg_str is None:
                continue

            ## Command: Start Moving ##
            if "BEGIN" in msg_str:
                if not self.check_api():
                    self.logger.error("API is down! Start command aborted.")

                self.clear_queues()
                # self.start_time = time.time_ns()
                self.command_queue.put("D", 0, 0, 0)

                # Small object direction detection

                self.small_direction = self.snap_and_rec("Small")
                self.logger.info(f"HERE small direction is: {self.small_direction}")
                if self.small_direction == "Left Arrow":
                    self.command_queue.put("OB01")  # ack_count = 3
                    self.command_queue.put("UL00")  # ack_count = 5
                elif self.small_direction == "Right Arrow":
                    self.command_queue.put("OB01")  # ack_count = 3
                    self.command_queue.put("UR00")  # ack_count = 5

                elif self.small_direction == None or self.small_direction == "None":
                    self.logger.info("Acquiring near_flag log")
                    self.near_flag.acquire()

                    self.command_queue.put("OB01")  # ack_count = 3

                self.logger.info(
                    "Start command received, starting robot on Week 9 task!"
                )
                self.android_queue.put("status, running")

                # Commencing path following | Main trigger to start movement #
                self.unpause.set()

    def recv_stm(self) -> None:
        """
        [Child Process] Receive acknowledgement messages from STM32, and release the movement lock
        """
        while True:
            message: str = self.stm.recv()
            # Acknowledgement from STM32
            if message.startswith("ACK"):
                self.ack_count += 1

                # Release movement lock
                try:
                    self.movement_lock.release()
                except Exception:
                    self.logger.warning("Tried to release a released lock!")

                self.logger.debug(
                    f"ACK from STM32 received, ACK count now:{self.ack_count}"
                )

                self.logger.info(f"self.ack_count: {self.ack_count}")
                if self.ack_count == 3:
                    try:
                        self.near_flag.release()
                        self.logger.debug(
                            "First ACK received, robot reached first obstacle!"
                        )
                        self.small_direction = self.snap_and_rec("Small_Near")
                        if self.small_direction == "Left Arrow":
                            self.command_queue.put("UL00")  # ack_count = 5
                        elif self.small_direction == "Right Arrow":
                            self.command_queue.put("UR00")  # ack_count = 5
                        else:
                            self.command_queue.put("UL00")  # ack_count = 5
                            self.logger.debug(
                                "Failed first one, going left by default!"
                            )
                    # except:
                    # self.logger.info("No need to release near_flag")

                    # if self.ack_count == 3:
                    except:
                        time.sleep(2)
                        self.logger.debug(
                            "First ACK received, robot finished first obstacle!"
                        )
                        self.large_direction = self.snap_and_rec("Large")
                        if self.large_direction == "Left Arrow":
                            self.command_queue.put("PL01")  # ack_count = 6
                        elif self.large_direction == "Right Arrow":
                            self.command_queue.put("PR01")  # ack_count = 6
                        else:
                            self.command_queue.put("PR01")  # ack_count = 6
                            self.logger.debug(
                                "Failed second one, going right by default!"
                            )

                if self.ack_count == 6:
                    self.logger.debug("Second ACK received from STM32!")
                    self.android_queue.put("status, finished")
                    self.command_queue.put("FIN")

                # except Exception:
                #     self.logger.warning("Tried to release a released lock!")
            else:
                self.logger.warning(f"Ignored unknown message from STM: {message}")

    # Done
    def android_sender(self) -> None:
        while True:
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
        while True:
            command: str = self.command_queue.get()
            self.unpause.wait()
            self.movement_lock.acquire()
            stm32_prefixes = ("D", "M", "S", "T", "W", "t", "w", "R", "r", "L", "l")
            if command.startswith(stm32_prefixes):
                self.stm.send(command)
            elif command == "FIN":
                self.unpause.clear()
                self.movement_lock.release()
                self.logger.info("Commands queue finished.")
                self.android_queue.put("info, Commands queue finished.")
                self.android_queue.put("status, finished")
                self.rpi_action_queue.put(PiAction(cat="stitch", value=""))
            else:
                raise Exception(f"Unknown command: {command}")

    def rpi_action(self):
        while True:
            action: PiAction = self.rpi_action_queue.get()
            self.logger.debug(
                f"PiAction retrieved from queue: {action.cat} {action.value}"
            )
            if action.cat == "snap":
                self.snap_and_rec(obstacle_id=action.value)
            elif action.cat == "stitch":
                self.request_stitch()

    def snap_and_rec(self, obstacle_id: str) -> None:
        """
        RPi snaps an image and calls the API for image-rec.
        The response is then forwarded back to the android
        :param obstacle_id: the current obstacle ID
        """
        self.logger.info(f"Capturing image for obstacle id: {obstacle_id}")
        self.android_queue.put(f"info, Capturing image for obstacle id: {obstacle_id}")
        url = f"http://{API_IP}:{API_PORT}/task2"
        filename = f"{int(time.time())}_{obstacle_id}.jpg"

        retry_count = 0

        while True:
            retry_count += 1
            file = Camera().capture_file()

            self.logger.debug("Requesting from image API")

            response = requests.post(
                url,
                files={"file": (file)},
            )

            if response.status_code != 200:
                self.logger.error(
                    "Something went wrong when requesting path from image-rec API. Please try again."
                )
                return

            results = json.loads(response.content)

            if results["image_id"] != "NA" or retry_count > 6:
                break
            elif retry_count <= 2:
                self.logger.info(f"Image recognition results: {results}")
                self.logger.info("Recapturing with same shutter speed...")
            elif retry_count <= 4:
                self.logger.info(f"Image recognition results: {results}")
                self.logger.info("Recapturing with lower shutter speed...")
            elif retry_count == 5:
                self.logger.info(f"Image recognition results: {results}")
                self.logger.info("Recapturing with lower shutter speed...")

        ans = SYMBOL_MAP.get(results["image_id"])
        self.logger.info(f"Image recognition results: {results} ({ans})")
        return ans

    # Done
    def request_stitch(self):
        url = f"http://{API_IP}:{API_PORT}/stitch"
        response = requests.get(url)
        if response.status_code != 200:
            self.logger.error(
                "Something went wrong when requesting stitch from the API."
            )
            return
        self.logger.info("Images stitched!")

    # Done
    def clear_queues(self):
        while not self.command_queue.empty():
            self.command_queue.get()

    # Done
    def check_api(self) -> bool:
        url = f"http://{API_IP}:{API_PORT}/status"
        try:
            response = requests.get(url, timeout=1)
            if response.status_code == 200:
                self.logger.debug("API is up!")
                return True
        except ConnectionError:
            self.logger.warning("API Connection Error")
            return False
        except requests.Timeout:
            self.logger.warning("API Timeout")
            return False
        except Exception as e:
            self.logger.warning(f"API Exception: {e}")
            return False


if __name__ == "__main__":
    rpi = RaspberryPi()
    rpi.start()
