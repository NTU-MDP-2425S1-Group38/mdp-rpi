import logging
import multiprocessing
import threading


class Singleton(type):
    """
    Singleton metaclass that is thread-safe.
    """
    _instances = {}
    _locks = {}  # Dictionary to hold locks for each class

    def __call__(cls, *args, **kwargs):
        # Ensure a lock exists for this class
        if cls not in Singleton._locks:
            Singleton._locks[cls] = threading.Lock()

        logging.getLogger().info(f"Attempting to acquire lock for {cls.__name__}")

        # Use the lock specific to this class
        with Singleton._locks[cls]:
            logging.getLogger().info(f"Lock acquired for {cls.__name__}")
            if cls not in Singleton._instances:
                logging.getLogger().info(f"Creating new instance of {cls.__name__}")
                Singleton._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
            else:
                logging.getLogger().info(f"Using existing instance of {cls.__name__}")
        return Singleton._instances[cls]
