import base64
import io
import logging
import threading
import picamera2
from PIL import Image
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



