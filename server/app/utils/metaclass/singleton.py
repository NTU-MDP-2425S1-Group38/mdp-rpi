import multiprocessing
import threading


class Singleton(type):
    """
    Singleton metaclass
    See original: https://stackoverflow.com/a/63483209
    ChatGPT thread/processing safe: https://chatgpt.com/share/185653f3-6d0b-4772-b997-42335c2fee0f
    """
    _process_lock = multiprocessing.Lock()  # A lock for synchronizing across processes

    def __init__(cls, *args, **kwargs):
        cls.__instance = None
        cls._manager = multiprocessing.Manager()  # Manager to create shared objects
        cls._shared_dict = cls._manager.dict()  # Shared dictionary across processes
        cls._thread_lock = threading.Lock()  # A lock for synchronizing threads within a process
        super().__init__(*args, **kwargs)

    def __call__(cls, *args, **kwargs):
        # Lock for multiprocessing
        with cls._process_lock:
            # Lock for multithreading within a process
            with cls._thread_lock:
                if cls.__instance is None and 'instance' not in cls._shared_dict:
                    cls.__instance = super().__call__(*args, **kwargs)
                    cls._shared_dict['instance'] = cls.__instance
                else:
                    cls.__instance = cls._shared_dict['instance']
        return cls.__instance
