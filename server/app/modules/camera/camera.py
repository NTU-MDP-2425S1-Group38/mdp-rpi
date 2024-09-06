import base64
import io
import picamera2


class Camera:
    """
    This class handles all camera interaction.
    Basically just reads from the camera (hopefully)
    """

    def __init__(self):
        # Initialize Picamera2
        self.cam = picamera2.Picamera2()

        # Configure the camera for capturing still images
        config = self.cam.create_still_configuration(main={"size": (640, 640)})

        # Configure and start the camera
        self.cam.configure(config)
        self.cam.start()


    def capture(self) -> str:
        """
        Method to read the image of the camera as a np array
        :return: Base64 image
        """

        # Create a BytesIO object to store the image in memory
        image_stream = io.BytesIO()

        # Capture the image in JPEG format
        self.cam.capture_file(image_stream, format='jpeg')

        # Move the pointer to the beginning of the BytesIO buffer
        image_stream.seek(0)

        # Convert the BytesIO buffer to base64
        image_base64 = base64.b64encode(image_stream.getvalue()).decode('utf-8')

        return image_base64
