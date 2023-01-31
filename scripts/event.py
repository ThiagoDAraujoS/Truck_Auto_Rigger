class Event:
    """ this is a simple c# style event, it does not feature a weak ref subscription system [yet],
        so be sure to unsubscribe before deleting subscribed objects """
    def __init__(self): self.event = []

    def __add__(self, other):
        self.event.append(other)
        return self

    def __sub__(self, other):
        self.event.remove(other)
        return self

    def __call__(self, *args, **kwargs):
        for method in self.event:
            method(*args, **kwargs)
