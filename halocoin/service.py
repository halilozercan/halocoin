import Queue
import sys
import threading
import warnings

import tools
from ntwrk.message import Order


class NoExceptionQueue(Queue.Queue):
    """
    In some cases, queue overflow is ignored. Necessary try, except blocks
    make the code less readable. This is a special queue class that
    simply ignores overflow.
    """

    def __init__(self, maxsize=0):
        Queue.Queue.__init__(self, maxsize)

    def put(self, item, block=True, timeout=None):
        try:
            Queue.Queue.put(self, item, block, timeout)
        except Queue.Full:
            pass


class Service:
    """
    Service is a background job synchronizer.
    It constitutes of an event loop, side threads and annotation helpers.
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
        self.__threads = {}

    def register(self):
        def service_target(service):
            service.set_state(Service.RUNNING)
            while service.get_state() == Service.RUNNING:
                try:
                    order = service.into_service_queue.get(timeout=1)
                    if isinstance(order, Order):
                        result = Service.execute_order(service, order)
                        self.service_responses[order.id] = result
                        self.signals[order.id].set()
                except TypeError:
                    service.set_state(Service.STOPPED)
                    self.service_responses[order.id] = True
                    self.signals[order.id].set()
                except Queue.Empty:
                    pass

        cont = self.on_register()
        if not cont:
            tools.log("Service is not going to continue with registering!")
            return False

        # Start event loop
        self.event_thread = threading.Thread(target=service_target, args=(self,), name=self.name)
        self.event_thread.start()

        # Start all side-threads
        for clsMember in self.__class__.__dict__.values():
            if hasattr(clsMember, "decorator"):
                if clsMember.decorator == threaded.__name__:
                    def threaded_wrapper(func):
                        def insider(*args, **kwargs):
                            while self.__threads[func.__name__][0]:
                                func(*args, **kwargs)
                            return 0

                        return insider

                    new_thread = threading.Thread(target=threaded_wrapper(clsMember._original),
                                                  args=(self,),
                                                  name=clsMember._original.__name__)
                    self.__threads[clsMember._original.__name__] = [True, new_thread]
                    new_thread.start()

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
        for key, thread in self.__threads.iteritems():
            thread[1].join()

        # If join is called from the service instance, there is no need to join.
        # Thread wants to destory itself
        if threading.current_thread().name != self.event_thread.name:
            self.event_thread.join()

        self.event_thread.join()

    def unregister(self):
        """
        Disconnect the service background operations.
        Close and join all side-threads and event loop.
        :return: None
        """
        self.execute('__shutdown_service__', True, args=(), kwargs={})
        self.join()
        self.on_close()

    def execute(self, action, expect_result, args, kwargs):
        """
        Execute an order that is triggered by annotated methods.
        This method should be treated as private.
        :param action: Action name
        :param expect_result: Whether to wait for result of action
        :param args: Argument list for method
        :param kwargs: Keyword argument list for method
        :return: result of action or None
        """
        if self.get_state() != Service.RUNNING:
            result = getattr(self, action)._original(self, *args, **kwargs)
            warnings.warn('You are running a background method on an unregistered service. {} {}'
                .format(action, self.__class__.__name__))
            return result

        result = None
        new_order = Order(action, args, kwargs)

        # This is already event thread and someone called a synced function.
        # We can run it now.
        if threading.current_thread().name == self.event_thread.name:
            result = Service.execute_order(self, new_order)
            return result

        self.signals[new_order.id] = threading.Event()
        self.into_service_queue.put(new_order)
        if expect_result:
            try:
                if self.signals[new_order.id].wait():
                    response = self.service_responses[new_order.id]
                    del self.signals[new_order.id]
                    del self.service_responses[new_order.id]
                    result = response
                else:
                    print 'Service wait timed out', self.__class__.__name__
            except:
                print sys.exc_info()
                pass
        return result

    @staticmethod
    def execute_order(service, order):
        """
        Directly executes the order on service instance.
        Makes no thread checks, no synchronization attempts.
        :param service: Service instance
        :param order: Order object
        :return: result of the execution
        """
        if order.action == '__close_threaded__':
            result = True
            service.__threads[order.args[0]][0] = False
        elif order.action == '__shutdown_service__':
            result = True
            for thread in service.__threads:
                thread[0] = False
            service.set_state(Service.STOPPED)
        elif hasattr(service, order.action):
            try:
                result = getattr(service, order.action)._original(service, *order.args, **order.kwargs)
            except:
                result = None
                tools.log(sys.exc_info())
        return result

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
            for thread in self.__threads.values():
                thread[0] = False
        self.__state = state

    def close_threaded(self):
        """
        Close current side-thread.
        :return: None
        """
        thread_name = threading.current_thread().name
        self.execute(action='__close_threaded__',
                     expect_result=True,
                     args=(thread_name,),
                     kwargs={})

    def threaded_running(self):
        """
        Should only be used by side-threads to check if it is
        still alive. Any inner loop can be cancelled.
        :return: is current side-thread should continue to run
        """
        thread_name = threading.current_thread().name
        is_service_running = (self.get_state() == Service.RUNNING)
        try:
            return self.__threads[thread_name][0] and is_service_running
        except:
            return True


def sync(func):
    """
    Decorator for any service method that needs to run in the event loop.
    Results return after execution.
    :param func: Function to be decorated
    :return: Decorated version of function
    """

    def wrapper(self, *args, **kwargs):
        return self.execute(func.__name__, True, args=args, kwargs=kwargs)

    wrapper._original = func
    wrapper.thread_safe = True
    return wrapper


def async(func):
    """
    Decorator for any service method that needs to run in the event loop.
    Results do not return after execution.
    :param func: Function to be decorated
    :return: Decorated version of function
    """

    def wrapper(self, *args, **kwargs):
        return self.execute(func.__name__, False, args=args, kwargs=kwargs)

    wrapper._original = func
    wrapper.thread_safe = True
    return wrapper


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
