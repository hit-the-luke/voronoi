from . import line
import bisect
import numpy as np
from . import event

class EventList(list):
    def __init__(self):
        super().__init__()
        self.intersections = dict()
        
    def insert(self, this_event, index=None):
        if index is None:
            index = bisect.bisect(self, this_event)
        if isinstance(this_event, event.IntersectionEvent):
            key = [this_event.line_1.serial_number, this_event.line_2.serial_number]
            key.sort()
            tuple(key)
            self.intersections[tuple(key)] = this_event
        super().insert(index, this_event)

    def remove(self, key: list):
        key.sort()
        this_event = self.intersections.get(tuple(key))
        if this_event is not None:
            self.pop(self.index(this_event))

    def test_order(self):
        for i in range(len(self) - 1):
            for j in range(i + 1, len(self)):
                if self[i] > self[j]:
                    self[i] > self[j]
                    assert self[i] > self[j]

    def show(self, fig):
        points = [np.stack((elem.point, elem.intersection_point), axis=0)
                  for elem in self if isinstance(elem, event.IntersectionEvent)]
        for points_this in points:
            fig.add_scatter(x=points_this[:, 0], y=points_this[:, 1], line_color='rgb(0,0,0)')
        points = np.array([elem.point for elem in self])
        uni, inv = np.unique(points, return_inverse=True, axis=0)
        texts = [' <br> '.join([str(j) + self[j].__repr__() for j in np.where(inv == i)[0]]) for i in inv]
        fig.add_scatter(x=points[:, 0], y=points[:, 1], text=texts, line_color='rgb(255, 180, 0)')

