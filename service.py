import Queue
import sys
import threading
import warnings

import tools
from ntwrk.message import Order


class Service:
    INIT = 0
    RUNNING = 1
    STOPPED = 2
    TERMINATED = 3

    def __init__(self, name):
        self.event_thread = threading.Thread()
        self.into_service_queue = Queue.Queue()
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
                        if order.action == '__close_threaded__':
                            self.__threads[order.args[0]][0] = False
                            self.service_responses[order.id] = True
                            self.signals[order.id].set()
                            self.__threads[order.args[0]][1].join()
                        elif hasattr(service, order.action):
                            try:
                                result = getattr(service, order.action)\
                                    ._original(service, *order.args, **order.kwargs)
                            except:
                                tools.log(sys.exc_info())
                                result = None
                                service.set_state(Service.TERMINATED)
                            self.service_responses[order.id] = result
                            self.signals[order.id].set()
                except Queue.Empty:
                    pass
                except TypeError:
                    service.set_state(Service.STOPPED)
                    self.service_responses[order.id] = True
                    self.signals[order.id].set()

        self.on_register()

        self.event_thread = threading.Thread(target=service_target, args=(self,), name=self.name)
        self.event_thread.start()

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
                                                  args=(self, ),
                                                  name=clsMember._original.__name__)
                    self.__threads[clsMember._original.__name__] = [True, new_thread]
                    new_thread.start()

    def on_register(self):
        # Implemented by subclass
        pass

    def on_close(self):
        # Implemented by subclass
        pass

    def unregister(self):
        self.execute(None, True, args=(), kwargs={})
        for key, thread in self.__threads.iteritems():
            thread[1].join()

        # If unregister is called from the service instance, there is no need to join.
        # Thread wants to destory itself
        if threading.current_thread().name != self.event_thread.name:
            self.event_thread.join()
        self.on_close()

    def execute(self, action, expect_result, args, kwargs):
        if self.get_state() != Service.RUNNING:
            result = getattr(self, action)._original(self, *args, **kwargs)
            warnings.warn('You are running a background method on an unregistered service. {} {}'.format(action, self.__class__.__name__))
            return result

        # We are already in event thread and someone called a synced function. Just run it.
        if threading.current_thread().name == self.event_thread.name:
            result = getattr(self, action)._original(self, *args, **kwargs)
            return result

        result = None
        new_order = Order(action, args, kwargs)
        self.signals[new_order.id] = threading.Event()
        self.into_service_queue.put(new_order)
        if expect_result:
            try:
                if self.signals[new_order.id].wait():
                    response = self.service_responses.pop(new_order.id)
                    result = response
                else:
                    print 'Service wait timed out', self.__class__.__name__
            except:
                print sys.exc_info()
                pass
        return result

    def set_state(self, state):  # (INIT|RUNNING|STOPPED|TERMINATED) -> ()
        if state == Service.STOPPED or state == Service.TERMINATED:
            for thread in self.__threads.values():
                thread[0] = False
        self.__state = state

    def get_state(self):  # () -> (INIT|RUNNING|STOPPED|TERMINATED)
        return self.__state

    def close_threaded(self):
        thread_name = threading.current_thread().name
        self.execute(action='__close_threaded__',
                     expect_result=True,
                     args=(thread_name,),
                     kwargs={})


def sync(func):

    def wrapper(self, *args, **kwargs):
        return self.execute(func.__name__, True, args=args, kwargs=kwargs)

    wrapper._original = func
    wrapper.thread_safe = True
    return wrapper


def async(func):

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
        warnings.warn('You are calling a threaded method. Threaded methods are ran once when service is registered.')
        return None

    wrapper.decorator = threaded.__name__
    wrapper._original = func
    return wrapper