import cv2
import numpy as np
from utils.metaclass.singleton import Singleton
import picamera2


class Camera():
    """
    This class handles all camera interaction.
    Basically just reads from the camera (hopefully)
    """

    def __init__(self):
        # Initialize Picamera2
        self.cam = picamera2.Picamera2()

        # Configure the camera for capturing still images
        config = self.cam.create_still_configuration()

        # Configure and start the camera
        self.cam.configure(config)
        self.cam.start()

    def capture(self) -> np.array:
        """
        Method to read the image of the camera as a np array
        :return:
        """
        frame = self.cam.capture_array()
        return frame
