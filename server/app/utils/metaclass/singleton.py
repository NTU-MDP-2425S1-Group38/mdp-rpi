import multiprocessing
import threading


class Singleton(type):
    """
    Singleton metaclass
    See original: https://stackoverflow.com/a/63483209
    ChatGPT thread/processing safe: https://chatgpt.com/share/185653f3-6d0b-4772-b997-42335c2fee0f
    """
    _process_lock = multiprocessing.Lock()

    def __init__(cls, *args, **kwargs):
        cls.__instance = None
        cls._thread_lock = threading.Lock()
        super().__init__(*args, **kwargs)

    def _get_or_create_shared_resources(cls):
        if not hasattr(cls, '_manager'):
            cls._manager = multiprocessing.Manager()
            cls._shared_dict = cls._manager.dict()
        return cls._shared_dict

    def __call__(cls, *args, **kwargs):
        with cls._process_lock:
            with cls._thread_lock:
                shared_dict = cls._get_or_create_shared_resources()
                if cls.__instance is None and 'instance' not in shared_dict:
                    cls.__instance = super().__call__(*args, **kwargs)
                    shared_dict['instance'] = cls.__instance
                else:
                    cls.__instance = shared_dict['instance']
        return cls.__instance
