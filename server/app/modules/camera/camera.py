import base64
import io
import logging
import threading
import picamera2
from PIL import Image
from utils.metaclass.singleton import Singleton
import time  # Importing time to generate timestamp
import os  # Importing os to use os.getlogin for user home directory


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
        # self.cam.start()
        self.logger.info("Camera has been configured!")

    def __del__(self):
        try:
            self.logger.info("Attempting to close camera()")
            self.cam.stop()
        except Exception:
            self.logger.info("Unable to stop camera, is it running?")

    def capture(self) -> str:
        """
        Method to read the image of the camera as a np array
        :return: Base64 image
        """

        # with self.lock:

        self.logger.info("Starting camera!")

        self.cam.start()  # this is the crux, picam2 doesn't throw errors if it is not start()'ed

        self.logger.info("Capturing image!")

        # Create a BytesIO object to store the image in memory
        image_stream = io.BytesIO()

        self.logger.info("Created bytes array")

        # Capture the image in JPEG format
        img = self.cam.capture_array()
        self.logger.info(f"Image! {img}")
        self.logger.info("Image has been captured as np.Array!")
        self.cam.stop()

        pil_img = Image.fromarray(img)
        pil_img.save(image_stream, format="JPEG", quality=70)

        return base64.b64encode(image_stream.getvalue()).decode("utf-8")

    def capture_file(self) -> io.BytesIO:
        """
        Method to capture an image, save it to a byte stream, and return the byte stream.
        :return: BytesIO stream of the captured image
        """

        self.logger.info("Starting camera!")

        self.cam.start()  # Ensure the camera is started

        self.logger.info("Capturing image!")

        # Capture the image in numpy array format
        img = self.cam.capture_array()
        self.logger.info(f"Image captured: {img.shape}")

        self.cam.stop()

        # Create a BytesIO object to store the image in memory
        image_stream = io.BytesIO()

        # Convert the numpy array to a PIL image
        pil_img = Image.fromarray(img)

        # Save the image to the BytesIO stream
        pil_img.save(image_stream, format="JPEG", quality=70)

        # Reset the stream position to the beginning so it can be read
        image_stream.seek(0)

        # Return the image stream
        return image_stream
