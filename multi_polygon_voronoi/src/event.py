import abc
import bisect
import numpy as np
import copy
import collections
import plotly.graph_objects

from . import line


class Event:
    def __init__(self, point):
        self.y = point[1]
        self.x = point[0]
        self.point = point

    def __lt__(self, other):
        if self.y < other.y:
            return True
        elif self.y > other.y:
            return False
        else:
            return self.lesser_than(other)

    @abc.abstractmethod
    def handle(self, beach_line, outer_bisectors, inner_bisectors, event_list, y_current, start_edges):
        pass

    @abc.abstractmethod
    def lesser_than(self, other):
        pass


class EndEvent(Event):
    def __init__(self, point, new_bisector, edge, new_line, dict_of_horizontals):
        super().__init__(point)
        self.direction_new_bisector_y = new_bisector.direction[1]
        self.new_bisector = new_bisector
        self.edge = edge
        self.new_line = new_line
        self.dict_of_horizontals = dict_of_horizontals

    def same_direction(self):
        return self.edge.is_forward == self.new_line.is_forward

    def show(self, fig=None):
        if fig is None:
            fig = plotly.grid_objs.Figure()
        self.edge.show(fig, color=(255, 125, 255), name='old')
        self.new_bisector.show(fig, color=(255, 125, 0), name='new_bisector')
        if self.edge.is_forward:
            self.edge.next.show(fig, color=(255, 125, 0), name='new')
        else:
            self.edge.previous.show(fig, color=(255, 125, 0), name='new')
        return fig

    def __repr__(self):
        return f"EndEvent: {self.point}, {self.new_bisector.direction}"

    def lesser_than(self, other):
        if isinstance(other, NewLineEvent):
            return False
        elif isinstance(other, IntersectionEvent):
            if self.edge.is_horizontal:
                if other.y in self.dict_of_horizontals:
                    index = bisect.bisect(self.dict_of_horizontals[self.y], other.x, key=lambda elem: elem[0])
                    if 0 < index < len(self.dict_of_horizontals[self.y]):
                        if self.dict_of_horizontals[self.y][index][1] == self.dict_of_horizontals[self.y][index - 1][1]:
                            return False
                return True
            return False
        else:
            if self.same_direction() and not other.same_direction():
                return True
            elif not self.same_direction() and other.same_direction():
                return False
            elif self.direction_new_bisector_y < other.direction_new_bisector_y:
                return True
            elif self.direction_new_bisector_y > other.direction_new_bisector_y:
                return False
            else:
                if self.edge.length() < other.edge.length():
                    return True
                elif self.edge.length() > other.edge.length():
                    return False
                else:
                    if self.x < other.x:
                        return True
                    elif self.x > other.x:
                        return False
                    else:
                        if self.edge.length() > 0 and other.edge.length() == 0:
                            return True
                        elif self.edge.length() == 0 and other.edge.length() > 0:
                            return False
                        elif self.edge.is_forward and not other.edge.is_forward:
                            return True
                        elif not self.edge.is_forward and other.edge.is_forward:
                            return False
                        else:
                            raise Exception('EndEvent: same point')

    def handle(self, beach_line, outer_bisectors, inner_bisectors, event_list, y_current, start_edges):
        if self.edge.is_done:
            return
        index_beach = beach_line.index(self.edge)
        if self.edge.is_horizontal and self.edge.length() == 0:
            if self.edge.is_forward:
                neighbour = beach_line[index_beach - 2]
            else:
                neighbour = beach_line[index_beach + 2]
            position_of_neighbour = neighbour.beach_position(self.y)
            if np.all(self.point != position_of_neighbour):
                line_to_neighbour = line.Line(self.point, position_of_neighbour)
                if self.new_bisector.direction[0] / line_to_neighbour.direction[0] > 0.5:
                    if self.edge.is_forward:
                        new_direction = line_to_neighbour.direction[::-1] * np.array([1, -1])
                        new_line = line.OutLine(self.point, self.point, self.edge.index_loop, new_direction)
                        self.edge.next.insert_lines_before([new_line])
                        self.new_bisector = new_line.bisector(self.edge)
                    else:
                        new_direction = line_to_neighbour.direction[::-1] * np.array([1, -1])
                        new_line = line.OutLine(self.point, self.point, self.edge.index_loop, new_direction)
                        self.edge.insert_lines_before([new_line])
                        self.new_bisector = self.edge.bisector(new_line)
        if self.edge.is_forward:
            new_line = self.edge.next
            self.edge.bisector_at_end = self.new_bisector
        else:
            new_line = self.edge.previous
            new_line.bisector_at_end = self.new_bisector
        if not new_line.is_in_beach_line:
            outer_bisectors.append(self.new_bisector)
            if self.edge.is_forward:
                index_insert_new_line = index_beach + 2
                index_insert_bisector = index_beach + 1
                beach_line.insert(index_insert_bisector, self.new_bisector)
                beach_line.insert(index_insert_new_line, new_line)
            else:
                index_insert_new_line = index_beach
                index_insert_bisector = index_beach + 1
                index_beach += 2
                beach_line.insert(index_insert_new_line, new_line)
                beach_line.insert(index_insert_bisector, self.new_bisector)
                self.new_bisector.is_in_beach_line = True
                new_line.is_forward = False
            new_line.is_in_beach_line = True
            if new_line.is_forward:
                end_point_new_line = new_line.end_point
                bisector = new_line.next.bisector(new_line)
                end_event_new = EndEvent(new_line.end_point, bisector, new_line, new_line.next, dict_of_horizontals=self.dict_of_horizontals)
            else:
                end_point_new_line = new_line.start_point
                bisector = new_line.bisector(new_line.previous)
                end_event_new = EndEvent(end_point_new_line, bisector, new_line, new_line.previous, dict_of_horizontals=self.dict_of_horizontals)
            if end_point_new_line[1] < y_current:
                print(end_point_new_line, y_current)
                fig = beach_line.show(self.point)
                self.show(fig)
                fig.show()
                print('hi')
            assert end_point_new_line[1] >= y_current
            event_list.insert(end_event_new)
        else:
            if not new_line.is_done:

                outer_bisectors.append(self.new_bisector)
                if self.edge.is_forward:
                    beach_line.insert(index_beach + 1, self.new_bisector)
                    try:
                        index_new_line = beach_line.index(new_line)
                    except Exception as ex:
                        raise ex
                    if index_beach > index_new_line:
                        index_beach -= 1
                    beach_line.remove(index_new_line)
                else:
                    beach_line.insert(index_beach, self.new_bisector)
                    try:
                        index_new_line = beach_line.index(new_line)
                    except Exception as ex:
                        fig = beach_line.show(self.point, self.y, do_display=False)
                        fig = self.show(fig)
                        fig.show()
                        raise ex
                    if index_beach < index_new_line:
                        index_beach += 1
                    beach_line.remove(index_new_line)
                beach_line.pop(index_new_line).is_done = True
        beach_line.remove(index_beach)
        beach_line.pop(index_beach).is_done = True


class IntersectionEvent(Event):
    def __init__(self, y_value, point, line_1, line_2):
        point_copy = copy.copy(point)
        point_copy[1] = y_value
        super().__init__(point_copy)
        self.line_1 = line_1
        self.line_2 = line_2
        self.intersection_point = point

    def lesser_than(self, other):
        if isinstance(other, NewLineEvent):
            return other.edge.direction[1] > 0
        else:
            if isinstance(other, EndEvent):
                return not other.lesser_than(self)
            else:
                for line_equal_self, line_different_self in ((self.line_1, self.line_2),
                                                             (self.line_2, self.line_1)):
                    for line_equal_other, line_different_other in ((other.line_1, other.line_2),
                                                                   (other.line_2, other.line_1)):
                        if line_equal_self == line_equal_other and line_different_self != line_different_other:
                            norm_self = np.linalg.norm(self.intersection_point - line_equal_self.start_point)
                            norm_other = np.linalg.norm(other.intersection_point - line_equal_other.start_point)
                            return norm_self < norm_other
                if self.x < other.x:
                    return True
                elif self.x > other.x:
                    return False

    def __repr__(self):
        return f"IntersectionEvent: ({self.line_1.serial_number}, {self.line_2.serial_number}, {self.intersection_point})"

    def show(self, fig):
        if fig is None:
            fig = plotly.graph_objects.Figure()
        self.line_1.show(fig, color=(255, 0, 125))
        self.line_2.show(fig, color=(255, 0, 125))
        return fig

    def handle(self, beach_line, outer_bisectors, inner_bisectors, event_list, y_current, start_edges):
        if self.line_1.is_done or self.line_2.is_done:
            return
        index_beach_line = beach_line.index(self.line_2)
        if self.line_1.serial_number == 8 or self.line_2.serial_number == 8:
            _ = 0
        if self.line_2.right.next == self.line_1.left:
            # handling the top end of polygon where left and right side merge again
            new_edge = self.line_1.left.bisector(self.line_2.right)
            self.line_2.right.bisector_at_end = new_edge
            new_edge.end_point = self.intersection_point
            new_edge.is_done = True
            outer_bisectors.append(new_edge)
            temp = beach_line.pop(index_beach_line)
            temp.end_point = self.intersection_point
            temp.is_done = True
            temp = beach_line.pop(index_beach_line - 1)
            temp.end_point = self.intersection_point
            temp.is_done = True
            beach_line.pop(index_beach_line - 2).is_done = True
            beach_line.pop(index_beach_line - 2).is_done = True
            new_edge.end_left = self.line_2
            new_edge.end_left_direction = -1
            new_edge.end_right = self.line_1
            new_edge.end_right_direction = -1
            self.line_1.end_right = self.line_2
            self.line_1.end_left = new_edge
            self.line_1.end_right_direction = -1
            self.line_1.end_left_direction = -1
            self.line_2.end_right = new_edge
            self.line_2.end_left = self.line_1
            self.line_2.end_right_direction = -1
            self.line_2.end_left_direction = -1
            if self.line_1.is_inner_bisector:
                if not self.line_2.is_inner_bisector:
                    if np.any(self.line_1.start_point == [-0.4286324250331163, -0.457238663838333]):
                        _ = 1
                    start_edges.append((self.line_1, -1))
            elif self.line_2.is_inner_bisector:
                if np.any(self.line_2.start_point == [-0.4286324250331163, -0.457238663838333]):
                    _ = 1
                start_edges.append((self.line_2, -1))
            return
        try:
            new_edge = self.line_2.right.bisector(self.line_1.left)
        except Exception as ex:
            fig = beach_line.show(self.intersection_point,
                                  limit=max(np.linalg.norm(self.intersection_point - self.point) * 1.2, 13))
            left_copy = copy.copy(self.line_1.left)
            right_copy = copy.copy(self.line_2.right)
            right_copy._end_point = right_copy.start_point + right_copy.direction
            left_copy._end_point = left_copy.start_point + left_copy.direction
            right_copy.show(fig=fig, color=(0, 255, 255), name='right_copy')
            left_copy.show(fig=fig, color=(0, 255, 255), name='left_copy')
            fig.show()
            raise ex
        new_edge.start_right = self.line_2
        new_edge.start_right_direction = - 1
        new_edge.start_left = self.line_1
        new_edge.start_left_direction = -1
        new_edge.is_inner_bisector = True
        if (not self.line_1.is_inner_bisector) and (not self.line_2.is_inner_bisector):
            if np.any(new_edge.start_point == [-0.4286324250331163, -0.457238663838333]):
                _ = 1
            start_edges.append((new_edge, 1))
        self.line_2.end_right = new_edge
        self.line_2.end_right_direction = 1
        self.line_2.end_left = self.line_1
        self.line_2.end_left_direction = -1
        self.line_1.end_right = self.line_2
        self.line_1.end_right_direction = -1
        self.line_1.end_left = new_edge
        self.line_1.end_left_direction = 1
        temp = beach_line.pop(index_beach_line)
        temp.end_point = self.intersection_point
        temp.is_done = True
        try:
            beach_line[index_beach_line - 1].end_point = beach_line[index_beach_line - 1].end_point
        except AttributeError as ex:
            raise ex
        else:
            temp = beach_line.pop(index_beach_line - 1)
            temp.end_point = self.intersection_point
            temp.is_done = True
        new_edge.start_point = self.intersection_point
        beach_line.insert(index_beach_line - 1, new_edge)
        inner_bisectors.append(new_edge)


class NewLineEvent(Event):
    def __init__(self, point, edge, dict_of_horizontals):
        super().__init__(point)
        self.edge = edge
        self.dict_of_horizontals = dict_of_horizontals

    def __repr__(self):
        return f"NewLineEvent: {self.point}"

    def lesser_than(self, other):
        if not isinstance(other, NewLineEvent):
            return self.edge.direction[1] < 0
        else:
            if self.x < other.x:
                return True
            elif self.x > other.x:
                return False
            else:
                raise Exception('NewLineEvent: same point')

    def show(self, fig=None):
        if fig is None:
            fig = plotly.graph_objects.Figure()
        self.edge.show(fig, color=(255, 125, 255), name='new_edge')
        self.edge.left.show(fig, color=(255, 125, 0), name='left')
        self.edge.right.show(fig, color=(255, 125, 0), name='right')
        return fig

    def handle(self, beach_line, outer_bisectors, inner_bisectors, event_list, y_current, start_edges):
        line.Line.y_current = self.y
        index_beach_line = bisect.bisect(beach_line, self.edge)
        if self.edge.direction[1] == -1:
            before = beach_line[index_beach_line - 1]
            after = beach_line[index_beach_line]
            point_before = before.beach_position(self.edge.start_point[1])
            point_after = after.beach_position(self.edge.start_point[1])
            x_new = self.edge.start_point[0]
            y_new = point_before[1] + (x_new - point_before[0]) / (point_after[0] - point_before[0]) * (
                    point_after[1] - point_before[1])
            self.edge.end_point = np.array([x_new, y_new])
            self.edge.is_in_beach_line = True
            self.edge.is_done = True
            outer_bisectors.append(self.edge)
            if isinstance(before, line.LineBisector):
                bisector1 = self.edge.right.bisector(before.right)
                bisector2 = before.right.bisector(self.edge.left)
            else:
                bisector1 = self.edge.right.bisector(before)
                bisector2 = before.bisector(self.edge.left)
            bisector1.is_inner_bisector = True
            bisector2.is_inner_bisector = True
            inner_bisectors.extend((bisector1, bisector2))
            bisector1.start_point[:] = (x_new, y_new)
            bisector2.start_point[:] = (x_new, y_new)
            beach_line.insert(index_beach_line, bisector2)
            beach_line.insert(index_beach_line, self.edge.left)
            self.edge.left.bisector_at_end = self.edge
            beach_line.insert(index_beach_line, self.edge.right)
            beach_line.insert(index_beach_line, bisector1)
            bisector1.start_right = self.edge
            bisector1.start_right_direction = -1
            bisector2.start_left = self.edge
            bisector2.start_left_direction = -1
            bisector1.start_left = bisector2
            bisector1.start_left_direction = 1
            bisector2.start_right = bisector1
            bisector2.start_right_direction = 1
            self.edge.end_right = bisector1
            self.edge.end_right_direction = 1
            self.edge.end_left = bisector2
            self.edge.end_left_direction = 1
            new_event = EndEvent(self.edge.left.start_point, self.edge.left.bisector(self.edge.left.previous),
                                 self.edge.left, self.edge.left.previous, dict_of_horizontals=self.dict_of_horizontals)
            event_list.insert(new_event)
            new_event = EndEvent(self.edge.right.end_point, self.edge.right.next.bisector(self.edge.right),
                                 self.edge.right, self.edge.right.next, dict_of_horizontals=self.dict_of_horizontals)
            event_list.insert(new_event)
        else:
            beach_line.insert(index_beach_line, self.edge.right)
            this_event = EndEvent(self.edge.right.end_point, self.edge.right.next.bisector(self.edge.right),
                                  self.edge.right, self.edge.right.next, dict_of_horizontals=self.dict_of_horizontals)
            try:
                event_list.insert(this_event)
            except Exception as ex:
                raise ex
            beach_line.insert(index_beach_line, self.edge)
            beach_line.insert(index_beach_line, self.edge.left)
            this_event = EndEvent(self.edge.left.start_point, self.edge.left.bisector(self.edge.left.previous),
                                  self.edge.left, self.edge.left.previous, dict_of_horizontals=self.dict_of_horizontals)
            event_list.insert(this_event)
            self.edge.is_in_beach_line = True
            self.edge.right.is_in_beach_line = True
            self.edge.left.is_in_beach_line = True
            self.edge.left.bisector_at_end = self.edge
            assert isinstance(self.edge, line.LineBisector)
            outer_bisectors.append(self.edge)
