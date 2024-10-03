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

    def capture_file(self, obstacle_id: str) -> str:
        """
        Method to capture an image, save it to a file, and return the filename.
        :param obstacle_id: ID related to the obstacle
        :param signal: The signal for the capture event
        :return: Filename of the saved image
        """

        self.logger.info("Starting camera!")

        self.cam.start()  # this is the crux, picam2 doesn't throw errors if it is not start()'ed

        self.logger.info("Capturing image!")

        # Create a BytesIO object to store the image in memory
        image_stream = io.BytesIO()

        # Capture the image in JPEG format
        img = self.cam.capture_array()
        self.logger.info(f"Image captured: {img.shape}")

        self.cam.stop()

        # Save the image to a file
        timestamp = int(time.time())  # Generate timestamp
        filename = f"{timestamp}_{obstacle_id}.jpg"
        self.logger.info(f"Saving image as {filename}")

        # Get the home directory of the current user
        home_dir = os.path.expanduser(f"~/{filename}")

        pil_img = Image.fromarray(img)
        pil_img.save(home_dir, format="JPEG", quality=70)

        # Encode the image to base64 (if you still need this part)
        # pil_img.save(image_stream, format="JPEG", quality=70)
        # base64_image = base64.b64encode(image_stream.getvalue()).decode("utf-8")

        # Return the filename (the full path where it's saved)
        return home_dir
