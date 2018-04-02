import queue
import threading
import traceback

from halocoin import tools


class NoExceptionQueue(queue.Queue):
    """
    In some cases, queue overflow is ignored. Necessary try, except blocks
    make the code less readable. This is a special queue class that
    simply ignores overflow. It is not a safe method and should never be used
    in production.
    """

    def __init__(self, maxsize=0):
        queue.Queue.__init__(self, maxsize)

    def put(self, item, block=False, timeout=None):
        try:
            queue.Queue.put(self, item, block, timeout)
        except queue.Full:
            pass


class Service:
    INIT = 0
    RUNNING = 1
    STOPPED = 2
    TERMINATED = 3

    def __init__(self, name):
        self.loop_thread = threading.Thread()
        self.name = name
        self.__state = None
        self.set_state(Service.INIT)

    def register(self):
        def threaded_wrapper(func):
            def insider(*args, **kwargs):
                while self.get_state() == Service.RUNNING:
                    try:
                        func(*args, **kwargs)
                    except Exception as e:
                        tools.log('Exception occurred at thread {}\n{}'.format(func.__name__, traceback.format_exc()))
                        self.set_state(Service.TERMINATED)
                return 0

            return insider

        cont = self.on_register()
        if not cont:
            tools.log("Service is not going to continue with registering!")
            return False

        self.loop_thread = threading.Thread(target=threaded_wrapper(self.loop),
                                            args=(),
                                            name=self.__class__.__name__ + "-" + self.loop.__name__)

        self.set_state(Service.RUNNING)
        self.loop_thread.start()
        return True

    # Lifecycle events
    def on_register(self):
        """
        Called just before registration starts.
        :return: bool indicating whether registration should continue
        """
        return True

    def loop(self):
        """
        Implemented by the extending class. This function is called repeatedly until service is
        shut down. Works the same as old "threaded" decorator.
        :return:
        """
        pass

    def on_close(self):
        """
        Called after everything is shut down.
        :return: Irrelevant
        """
        return True

    def join(self):
        """
        Join the loop thread
        :return: None
        """
        self.loop_thread.join()

    def unregister(self):
        """
        Disconnect the service background operations.
        :return: None
        """
        self.set_state(Service.STOPPED)
        self.on_close()

    def get_state(self, readable=False):  # () -> (INIT|RUNNING|STOPPED|TERMINATED)
        """
        :return: State of the service
        """
        if readable:
            if self.__state == Service.RUNNING:
                return "RUNNING"
            if self.__state == Service.INIT:
                return "INIT"
            if self.__state == Service.STOPPED:
                return "STOPPED"
            if self.__state == Service.TERMINATED:
                return "TERMINATED"
        else:
            return self.__state

    def set_state(self, state):  # (INIT|RUNNING|STOPPED|TERMINATED) -> ()
        """
        Set the current state of the service.
        This should never be used outside of the service.
        Treat as private method.
        :param state: New state
        :return: None
        """
        self.__state = state

    def get_status(self):
        """
        To be implemented by child class
        :return:
        """
        return {
            "status": self.get_state(readable=True)
        }


locks = {}


class LockException(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)


def lockit(lock_name, timeout=-1):
    def _lockit(func):
        """
        Decorator for any service method that needs to run in the event loop.
        Results return after execution.
        :param func: Function to be decorated
        :return: Decorated version of function
        """

        def wrapper(self, *args, **kwargs):
            global locks
            if '__lock_{}__'.format(lock_name) in locks.keys():
                mylock = locks['__lock_{}__'.format(lock_name)]
            else:
                mylock = threading.RLock()
                locks['__lock_{}__'.format(lock_name)] = mylock
            is_acquired = mylock.acquire(timeout=timeout)
            if is_acquired:
                try:
                    result = func(self, *args, **kwargs)
                    mylock.release()
                    return result
                except Exception as e:
                    tools.log("Exception occurred in a locked function")
                    tools.log(e)
                    mylock.release()
                    raise e
            else:
                tools.log('Lock named {} could not be acquired in the given time'.format(lock_name))

        wrapper._original = func
        wrapper.thread_safe = True
        wrapper.__name__ = func.__name__
        return wrapper

    return _lockit
