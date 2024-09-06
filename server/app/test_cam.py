from modules.camera.camera import Camera


def main():
    cam = Camera()

    while True:
        print(cam.capture())


if __name__ == "__main__":
    main()
