import queue
import threading
import traceback

from halocoin import tools


class NoExceptionQueue(queue.Queue):
    """
    In some cases, queue overflow is ignored. Necessary try, except blocks
    make the code less readable. This is a special queue class that
    simply ignores overflow.
    """

    def __init__(self, maxsize=0):
        queue.Queue.__init__(self, maxsize)

    def put(self, item, block=False, timeout=None):
        try:
            queue.Queue.put(self, item, block, timeout)
        except queue.Full:
            pass


class Service:
    """
    Service is a background job synchronizer.
    It consists of an event loop, side threads and annotation helpers.
    Event loop starts listening for upcoming events after registration.
    If service is alive, all annotated methods are run in background
    thread and results return depending on annotation type.

    Side threads are executed repeatedly until service shuts down or
    thread is forcefully closed from another thread. Each side-thread should
    also check for infinite loops.
    """
    INIT = 0
    RUNNING = 1
    STOPPED = 2
    TERMINATED = 3

    def __init__(self, name):
        self.event_thread = threading.Thread()
        self.into_service_queue = NoExceptionQueue(1000)
        self.signals = {}
        self.service_responses = {}
        self.name = name
        self.__state = None
        self.execution_lock = threading.Lock()
        self._threads = {}

    def register(self):
        def threaded_wrapper(func):
            def insider(*args, **kwargs):
                while self._threads[func.__name__]["running"]:
                    try:
                        func(*args, **kwargs)
                    except Exception as e:
                        tools.log('Exception occurred at thread {}\n{}'.format(func.__name__, traceback.format_exc()))
                return 0

            return insider

        cont = self.on_register()
        if not cont:
            tools.log("Service is not going to continue with registering!")
            return False

        # Start all side-threads
        for clsMember in self.__class__.__dict__.values():
            if hasattr(clsMember, "decorator") and clsMember.decorator == threaded.__name__:
                new_thread = threading.Thread(target=threaded_wrapper(clsMember._original),
                                              args=(self,),
                                              name=clsMember._original.__name__)
                self._threads[clsMember._original.__name__] = {
                    "running": True,
                    "thread": new_thread
                }
                new_thread.start()

        self.set_state(Service.RUNNING)
        return True

    # Lifecycle events
    def on_register(self):
        """
        Called just before registration starts.
        :return: bool indicating whether registration should continue
        """
        return True

    def on_close(self):
        """
        Called after everything is shut down.
        :return: Irrelevant
        """
        return True

    def join(self):
        """
        Join all side-threads and event loop in the end.
        :return: None
        """
        for thread_dict in self._threads.values():
            thread_dict["thread"].join()

        self.into_service_queue.join()

    def unregister(self, join=False):
        """
        Disconnect the service background operations.
        Close and join all side-threads and event loop.
        :return: None
        """
        for name in self._threads.keys():
            self._threads[name]['running'] = False
        if join:
            self.join()
        self.on_close()

    def get_state(self):  # () -> (INIT|RUNNING|STOPPED|TERMINATED)
        """
        :return: State of the service
        """
        return self.__state

    def set_state(self, state):  # (INIT|RUNNING|STOPPED|TERMINATED) -> ()
        """
        Set the current state of the service.
        This should never be used outside of the service.
        Treat as private method.
        :param state: New state
        :return: None
        """
        if state == Service.STOPPED or state == Service.TERMINATED:
            tools.log('{} got stopped'.format(self.__class__.__name__))
            for thread_name in self._threads.keys():
                self._threads[thread_name]["running"] = False
        self.__state = state

    def threaded_running(self):
        """
        Should only be used by side-threads to check if it is
        still alive. Any inner loop can be cancelled.
        :return: is current side-thread should continue to run
        """
        thread_name = threading.current_thread().name
        is_service_running = (self.get_state() == Service.RUNNING)
        try:
            return self._threads[thread_name]["running"] and is_service_running
        except:
            return False


def threaded(func):
    """
    This is just a marker decorator. It removes all the functionality but
    adds a decorator marker so that it can be registered as a new thread

    Given method assumed to be running indefinitely until a closing signal is given.
    That's why threaded methods should define their own while or for loop. Instead,
    signal close by using an if condition at the start of the method.
    Close signal can be given out by Service.close_threaded()
    :param func: Function to be marked
    :return: useless function that is marked
    """

    def wrapper(self, *args, **kwargs):
        import warnings
        warnings.warn('Threaded methods should not be executed directly.')
        return None

    wrapper.decorator = threaded.__name__
    wrapper._original = func
    return wrapper


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