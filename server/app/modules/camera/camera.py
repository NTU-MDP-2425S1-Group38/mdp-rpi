import cv2
import numpy as np
from utils.metaclass.singleton import Singleton


class Camera():
    """
    This class handles all camera interaction.
    Basically just reads from the camera (hopefully)
    """

    def __init__(self):
        self.cam = cv2.VideoCapture(0)


    def capture(self) -> np.array:
        """
        Method to read the image of the camera as a np array
        :return:
        """
        _, frame = self.cam.read()
        return frame
