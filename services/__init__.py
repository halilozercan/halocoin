pool = {}


def register(service):
    pool[service.name] = service
    service.register()


def unregister(service_name=None):
    if service_name is not None:
        service = pool[service_name]
        service.unregister()
        del pool[service_name]
    else:
        for name in pool.keys():
            unregister(name)


def get(name):
    return pool[name]