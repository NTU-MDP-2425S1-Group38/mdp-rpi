import base64
import io
import logging
import threading

import picamera2
from utils.metaclass.singleton import Singleton


class Camera(metaclass=Singleton):
    """
    This class handles all camera interaction.
    Basically just reads from the camera (hopefully)
    """

    logger = logging.getLogger("Camera")

    def __init__(self):
        # Initialize Picamera2
        self.logger.info("Starting Picamera!")
        self.cam = picamera2.Picamera2()

        self.lock = threading.Lock()

        # Configure the camera for capturing still images
        config = self.cam.create_still_configuration(queue=False)

        # Configure and start the camera
        self.cam.configure(config)
        self.cam.start()
        self.logger.info("Camera has started!")


    def capture(self) -> str:
        """
        Method to read the image of the camera as a np array
        :return: Base64 image
        """

        with self.lock:

            self.cam.start()

            self.logger.info("Capturing image!")

            # Create a BytesIO object to store the image in memory
            image_stream = io.BytesIO()

            self.logger.info("Created bytes array")

            # Capture the image in JPEG format
            self.logger.info(self.cam.capture_array())
            #
            self.logger.info("Image has been captured as np.Array!")

            self.cam.stop()

            return ""

        # # Move the pointer to the beginning of the BytesIO buffer
        # image_stream.seek(0)
        #
        # # Convert the BytesIO buffer to base64
        # image_base64 = base64.b64encode(image_stream.getvalue()).decode('utf-8')
        #
        # self.logger.info("Image has been captured as base64!")
        #
        # return image_base64
