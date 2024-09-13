import logging
import multiprocessing
import threading


class Singleton(type):
    """
    Singleton metaclass that is thread-safe.
    """
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        logging.getLogger().info(f"Attempting to acquire lock for {cls.__name__}")
        with cls._lock:  # Use the class-level lock
            logging.getLogger().info(f"Lock acquired for {cls.__name__}")
            if cls not in cls._instances:
                logging.getLogger().info(f"Creating new instance of {cls.__name__}")
                cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
            else:
                logging.getLogger().info(f"Using existing instance of {cls.__name__}")
        return cls._instances[cls]
