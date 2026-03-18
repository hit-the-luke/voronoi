import copy

import numpy as np
import plotly.graph_objects as go


class Point:
    def __init__(self, coordinates):
        self.coordinates = coordinates


class Vertex:
    def __init__(self, point):
        self.point = point
        self.edges = []


FACTOR = 1


class Line:
    serial_number_counter = 0
    y_current = None

    def __init__(self, origin: np.array, end_point=None, direction=None):
        if np.any(np.isnan(origin)):
            raise Exception
        self.serial_number = Line.serial_number_counter
        Line.serial_number_counter += 1
        self.origin = origin
        if end_point is None and direction is None:
            raise ValueError("end_point and direction are None")
        self._end_point = end_point
        self._direction = direction
        self._length = None
        self.is_in_beach_line = False
        self.is_done = False

    @property
    def min_y(self):
        return min(self.start_point[1], self.end_point[1])

    @property
    def min_x(self):
        return min(self.start_point[0], self.end_point[0])

    @property
    def y_max(self):
        return max(self.start_point[1], self.end_point[1])

    @property
    def x_max(self):
        return max(self.start_point[0], self.start_point[0])

    @property
    def direction(self):
        if self._direction is None:
            diff = self.end_point - self.start_point
            norm = np.linalg.norm(diff)
            if norm == 0:
                print(self.serial_number)
                pass
                # raise Exception('hi')
            self._direction = diff / norm
        return self._direction

    @property
    def end_point(self):
        if self._end_point is None:
            return self.start_point + self._direction
        else:
            return self._end_point

    @end_point.setter
    def end_point(self, value):
        self._direction = None
        self._end_point = value

    @property
    def start_point(self):
        return self.origin

    @property
    def is_horizontal(self):
        return self.direction[1] == 0

    @property
    def y_sorting(self):
        return self.min_y

    @property
    def x_sorting(self):
        return self.min_x

    def intersection(self, other, return_k=False, return_both_k=False):
        determinant = self.direction[0] * other.direction[1] - self.direction[1] * other.direction[0]
        if determinant == 0:
            temp1 = np.stack((self.start_point, self.end_point), axis=0)
            temp2 = np.stack((other.start_point, other.end_point), axis=0)
            temp1 = np.concatenate((temp1,) * 2, axis=0)
            temp2 = np.repeat(temp2, 2, axis=0)
            res = np.where(np.all(temp1 == temp2, axis=1))[0]
            if len(res):
                if res[0] < 2:
                    res = self.start_point
                    if return_k:
                        return res, 0
                    if return_both_k:
                        return res, 0, other.length()
                else:
                    res = self.end_point
                    if return_k:
                        return res, self.length()
                    if return_both_k:
                        return res, self.length(), 0
            else:
                if return_k:
                    return self.origin + other.origin, np.inf
                else:
                    return self.origin + other.origin, np.inf, np.inf
            k = np.inf
        else:
            dp = other.origin - self.origin
            k = (dp[0] * other.direction[1] - dp[1] * other.direction[0]) / determinant
            if return_both_k:
                other_k = (dp[0] * self.direction[1] - dp[1] * self.direction[0]) / determinant
                return self.origin + k * self.direction, k, other_k
        if return_k:
            return self.origin + k * self.direction, k
        else:
            return self.origin + k * self.direction

    def length(self):
        return np.linalg.norm(self.start_point - self.end_point)

    def __neg__(self):
        if len(self._direction):
            return Line(self.end_point, self.start_point, -self._direction)
        else:
            return Line(self.end_point, self.start_point)

    def orient(self):
        if self.direction[1] > 0:
            return self
        elif self.direction[1] < 0:
            return -self
        else:
            if self.direction[0] < 0:
                return -self
            else:
                return self

    def show(self, fig=None, color=None, name=None):
        if fig is None:
            fig = go.Figure()
        temp = np.stack((self.start_point, self.end_point), -1) * FACTOR
        line_dict = dict()
        if color is not None:
            line_dict['color'] = f"rgb{color}"
        else:
            line_dict['color'] = "rgb(0, 0, 255)"
        fig.add_scatter(x=temp[0], y=temp[1], line=line_dict, name=name)
        if self.length() == 0:
            temp = np.stack((self.start_point, self.start_point + self.direction), -1) * FACTOR
            line_dict = dict()
            if color is not None:
                line_dict['color'] = f"rgb{color}"
            else:
                line_dict['color'] = "rgb(0, 0, 255)"
            line_dict['dash'] = 'dash'
            fig.add_scatter(x=temp[0], y=temp[1], line=line_dict, name=name)
        return fig

    def beach_position(self, y):
        if self.start_point[1] == self.end_point[1]:
            if y >= self.start_point[1]:
                return self.end_point
            else:
                return self.start_point
        return np.array([self.origin[0] + (y - self.origin[1]) / self.direction[1] * self.direction[0], y])

    def __repr__(self):
        return f'Line{self.serial_number}({self.start_point.tolist()}, {self.end_point.tolist()})'

    def __lt__(self, other):

        beach_position_other = other.beach_position(self.y_current)[0]
        if beach_position_other > self.x_sorting:
            return True
        elif beach_position_other < self.x_sorting:
            return False
        else:
            right_self = self.direction[0] > 0
            right_other = other.direction[0] > 0
            if right_other > right_self:
                return True
            elif right_other < right_self:
                return False
            elif right_self:
                return self.direction[0] < other.line.direction[0]
            else:
                return self.direction[0] > other.line.direction[0]

    def show_to_beach_line(self, y, fig=None, color=None, name=None):
        end_point_stored = self.end_point
        current_endpoint = self.beach_position(y)
        if current_endpoint[1] <= end_point_stored[1]:
            self._end_point = current_endpoint
            res = self.show(fig, color, name)
            self._end_point = end_point_stored
        else:
            res = self.show(fig, color, name)
        return res

    def get_distance_to_point(self, point):
        return np.cross(point - self.origin, self.direction)

    def turn_right(self, other):
        return np.cross(self.direction, other.direction) < -10**-6

    def is_parallel(self, other):
        return np.abs(np.cross(self.direction, other.direction)) < 5*10**-7

    def distance(self, point):
        if self.length():
            res = np.dot((point - self.start_point), self.direction)
            if 0 < res < 1:
                return np.linalg.norm((self.start_point + self.direction * res) - point)
            elif res <= 0:
                return np.linalg.norm(self.start_point - point)
            else:
                return np.linalg.norm(self.end_point - point)
        return np.min(np.linalg.norm([self.start_point - point]))

    def angle(self, other):
        cross = np.cross(self.direction, other.direction)
        dot = np.dot(self.direction, other.direction)
        if dot > 0.5:
            angle = np.arcsin(cross)
        elif dot < -0.5:
            if cross == 0:
                angle = np.pi
            else:
                angle = np.sign(cross) * np.pi - np.arcsin(cross)
        else:
            angle = np.sign(cross) * np.arccos(dot)
        return angle


class OutLine(Line):
    def __init__(self, origin, end_point, index_loop, direction=None):
        super().__init__(origin, end_point, direction)
        self.next = None
        self.previous = None
        self.is_forward = self.calc_is_forward()
        self.is_heading_right = True
        self.index_loop = index_loop
        self._bisector_at_end = None
        if origin[0] > end_point[0]:
            self.is_heading_right = False


    def __repr__(self):
        return f'OutLine{self.serial_number}({self.start_point.tolist()}, {self.end_point.tolist()})'

    @property
    def bisector_at_end(self):
        return self._bisector_at_end

    @bisector_at_end.setter
    def bisector_at_end(self, value):
        if value is not None  and np.any(value.start_point != self.end_point):
            _ = 0
        self._bisector_at_end = value

    def calc_is_forward(self):
        if self.origin[1] > self.end_point[1]:
            return False
        if self.origin[1] < self.end_point[1]:
            return True
        if self.origin[0] > self.end_point[0]:
            return False
        if self.origin[0] < self.end_point[0]:
            return True
        if self.direction[1] < 0:
            return False
        if self.direction[1] > 0:
            return True
        return self.direction[0] > 0

    def bisector(self, other):
        return LineBisector(other, self)

    @property
    def y_sorting(self):
        return self.min_y

    @property
    def x_sorting(self):
        return self.min_x

    def insert_lines_before(self, edges_to_insert):
        previous = self.previous
        for i in range(0, len(edges_to_insert) - 1):
            edges_to_insert[i].next = edges_to_insert[i+1]
            edges_to_insert[i+1].previous = edges_to_insert[i]
        edges_to_insert[0].previous = previous
        previous.next= edges_to_insert[0]
        edges_to_insert[-1].next = self
        self.previous = edges_to_insert[-1]

    def remove_line(self):
        previous_line = self.previous
        next_line = self.next
        previous_line.end_point = self.end_point
        previous_line.next = next_line
        next_line.previous = previous_line

    def split_at_closest_point(self, point):
        if np.any(np.all(np.abs(point - np.array([[0.70912624, 3.77355014]])) < 10**-6)):
            _ = 1
        if self.length():
            res = np.dot((point - self.start_point), self.direction)
            if 0 < res < self.length():
                point_split = self.origin + self.direction * res
                line_new = type(self)(point_split, self.end_point, self.direction)
                line_new.next = self.next
                self.next.previous = line_new
                line_new.previous = self
                self.next = line_new
                self.end_point = point_split
                return True
        return False


class LineBisector(Line):
    def __init__(self, left, right):

        if np.any(np.all(np.abs(left.start_point - np.array([1.6449862737848333, 3.2574519582469157]))< 10**-6)):
            _ = 1
        self._k_start_point = None
        self._k_end_point = None
        self._thick_at_end = None
        self._angle_to_left = None
        temp = right.direction + left.direction
        if np.all(np.abs(temp) < 10 ** -5):
            self.parallel = True
            new_direction = right.direction
            origin = (left.end_point + right.start_point) / 2
            temp = origin - right.start_point
            self.distance_half = np.abs(temp[0] * new_direction[1] - temp[1] * new_direction[0])
            self.bisector_angle = 0
        else:
            self.parallel = False
            self.distance_half = None
            temp[:] = (-temp[-1], temp[0])
            new_direction = temp / np.linalg.norm(temp)
            origin, k_right, k_left = right.intersection(left, return_both_k=True)
            if left.next == right:  # or right.next == left:
                direction_sign = 1
            else:
                if right.length() > 0:
                    if k_right > (1 - 10 ** -6) * right.length():
                        direction_sign = -1
                    elif k_right < 10 ** -6:
                        direction_sign = 1
                    else:
                        direction_sign = 0
                else:
                    direction_sign = -np.sign(k_right)
                if left.length() > 0:
                    if k_left > (1 - 10 ** -6) * left.length():
                        direction_sign += 1
                    elif k_left < 10 ** -6:
                        direction_sign += -1
                else:
                    direction_sign += np.sign(k_left)
            if direction_sign < 0:
                new_direction *= -1
                self.bisector_angle = -np.arccos(np.sum((-new_direction) * left.direction))
            elif direction_sign == 0:
                if k_right < 0 and k_left < 0:
                    self.bisector_angle = np.arccos(np.sum((-new_direction) * left.direction))
                elif left.length() == 0 or right.length() == 0:
                    self.bisector_angle = np.arccos(np.sum((-new_direction) * left.direction))
                else:
                    raise Exception('Trying to get bisector of intersecting lines')
            else:
                self.bisector_angle = np.arccos(np.sum((-new_direction) * left.direction))
        if left.next == right:
            origin = left.end_point
        super().__init__(origin=origin, direction=new_direction)
        self.left = left
        self.right = right
        self._start_point = copy.copy(origin)
        self.next_intersection = None
        self.start_left = None
        self.start_left_direction = None
        self.start_right = None
        self.start_right_direction = None
        self.end_left = None
        self.end_left_direction = None
        self.end_right = None
        self.end_right_direction = None
        self.is_inner_bisector = False

    @property
    def y_sorting(self):
        return self.start_point[1]

    @property
    def x_sorting(self):
        return self.start_point[0]

    @property
    def angle_to_left(self):
        if self.serial_number == 28:
            _ = 0
        if self._angle_to_left is None:
            self._angle_to_left = self.left.angle(self)
        return self._angle_to_left

    def beach_position(self, y):
        if self.parallel:
            if np.abs(self.direction[1]) < 10 ** -6:
                return self.start_point
            l = (y - self.origin[1] - self.distance_half) / self.direction[1]
        else:
            left_side_horizontal = np.abs(self.left.direction[1]) < 10 ** -8
            right_side_horizontal = np.abs(self.right.direction[1]) < 10 ** -8
            if left_side_horizontal or right_side_horizontal:
                left_side_up = self.direction[0] > 0
                right_side_up = self.direction[0] < 0
                if (left_side_up and left_side_horizontal) or (right_side_up and right_side_horizontal):
                    if (self.direction[1] < 0 or (left_side_up and self.left.start_point[1] > self.start_point[1]) or
                            (right_side_horizontal and self.right.start_point[1] > self.start_point[1])):
                        return self.start_point
                l = (y - self.origin[1]) / self.direction[1] / 2
            else:
                divisor = (np.sin(self.bisector_angle) + self.direction[1])
                if np.abs(divisor) <= 10**-6:
                    assert np.abs(divisor) > 10 ** -6
                l = (y - self.origin[1]) / divisor
        return self.origin + self.direction * l

    def y_value(self, l):
        if self.parallel:
            return self.direction[1] * l + self.origin[1] + self.distance_half
        else:

            left_side_horizontal = np.abs(self.left.direction[1]) < 10 ** -6
            right_side_horizontal = np.abs(self.right.direction[1]) < 10 ** -6
            if left_side_horizontal or right_side_horizontal:
                left_side_up = self.direction[0] > 0
                right_side_up = self.direction[0] < 0
                if left_side_up and left_side_horizontal or right_side_up and right_side_horizontal:
                    return self.origin[1]
                else:
                    return l * self.direction[1] + l * np.abs(self.direction[1]) + self.origin[1]
            return l * (np.sin(self.bisector_angle) + self.direction[1]) + self.origin[1]

    @property
    def start_point(self):
        try:
            return self._start_point
        except AttributeError as ex:
            _ = 0
            raise ex

    @start_point.setter
    def start_point(self, value: np.ndarray):
        self._k_start_point = None
        self._start_point = value

    @property
    def end_point(self):
        return super().end_point

    @end_point.setter
    def end_point(self, value):
        self._end_point = value

    def show(self, fig=None, color=None, name=None):
        if color is None:
            color = (255, 0, 0)
        return super().show(fig, color, name)

    def show_to_beach_line(self, y, fig=None, color=None, name=None):
        if color is None:
            color = (255, 0, 0)
        if self._end_point is None:
            self._end_point = np.array([0, y])
            res = super().show_to_beach_line(y, fig, color, name)
            self._end_point = None
            return res
        else:
            return super().show(fig, color, name)

    def __repr__(self):
        return f'LineBisector{self.serial_number}({self.start_point.tolist()}, {self.end_point.tolist()})'

    @property
    def k_start_point(self):
        if self._k_start_point is None:
            self._k_start_point = np.dot(self.start_point - self.origin, self.direction)
        return self._k_start_point

    @property
    def k_end_point(self):
        if self._k_end_point is None:
            self._k_end_point = np.dot(self.end_point - self.origin, self.direction)
        return self._k_end_point

    @property
    def thick_at_end(self):
        if self._thick_at_end is None:
            self._thick_at_end = np.linalg.norm(self.origin - self.start_point) < np.linalg.norm(self.origin - self.end_point)
        return self._thick_at_end

    def point_at_distance(self, distance):
        if np.abs(np.sin(self.angle_to_left)) * np.sign(self.k_end_point) == 0:
            _ = 0
        distance_adjusted = distance / np.abs(np.sin(self.angle_to_left)) * np.sign(self.k_end_point)
        try:
            if np.abs(distance_adjusted) < max(np.abs(self.k_end_point), np.abs(self.k_start_point)):
                pass
        except ValueError:
            _ = 0
        if np.abs(distance_adjusted) < max(np.abs(self.k_end_point), np.abs(self.k_start_point)):
            return [(self.origin + self.direction * distance_adjusted, self.serial_number)]
        else:
            if self.is_inner_bisector:
                return [None]
            else:
                points_at_distance = []
                try:
                    if self.end_left.is_inner_bisector and (self.end_left_direction == 1) == self.end_left.thick_at_end:
                        points_at_distance.append(self.end_left.point_at_distance(distance)[0])
                    else:
                        points_at_distance.append(None)
                    if self.end_right.is_inner_bisector and (self.end_right_direction == 1) == self.end_right.thick_at_end:
                        points_at_distance.append(self.end_right.point_at_distance(distance)[0])
                    else:
                        points_at_distance.append(None)
                except AttributeError as ex:
                    _ = 1
                    raise ex
                return points_at_distance


class LineBisectorDummy(Line):
    def __init__(self, left, right, origin, end_point, counterpart):
        super().__init__(origin=origin, end_point=end_point)
        self._thick_at_end = None
        self.left = left
        self.right = right
        self._start_point = copy.copy(origin)
        self.is_inner_bisector = False
        self.counterpart = counterpart
        self.k_start_point = 0
        self._k_end_point = None
        self._angle_to_left = abs(self.angle(left))

    @property
    def angle_to_left(self):
        if self._angle_to_left is None:
            self._angle_to_left = self.left.angle(self)
        return self._angle_to_left

    @property
    def k_end_point(self):
        if self._k_end_point is None:
            self._k_end_point = np.dot(self.end_point - self.origin, self.direction)
        return self._k_end_point

    @property

    @property
    def start_left(self):
        return None


    @property
    def start_left_direction(self):
        pass

    @property
    def start_right(self):
        pass

    @property
    def start_right_direction(self):
        pass

    @property
    def end_left(self):
        if self.counterpart is not None:
            return self.counterpart.end_right
        else:
            return None

    @property
    def end_left_direction(self):
        if self.counterpart is not None:
            return self.counterpart.end_right_direction
        else:
            return None

    @property
    def end_right(self):
        if self.counterpart is not None:
            return self.counterpart.end_left
        else:
            return None

    @property
    def end_right_direction(self):
        if self.counterpart is not None:
            return self.counterpart.end_left_direction
        else:
            return None

    def point_at_distance(self, distance):
        try:
            distance_adjusted = distance / np.sin(self.angle_to_left)
        except TypeError:
            _ = 1
            raise
        if np.abs(distance_adjusted) < np.abs(self.k_end_point):
            return [(self.origin + self.direction * distance_adjusted, self.serial_number)]
        else:
            if self.counterpart is None:
                return [None, None]
            else:
                return self.counterpart.point_at_distance(distance)[::-1]

# class Intersection:
#     def __init__(self, z_value, coords, line1, line2):
#         self.z_value = z_value
#         self.coords = coords,
#         self.line1 = line1
#         self.line2 = line2
#
#
# class InsertionSorter:
#     def __init__(self, line: Line):
#         self.line = line
#
#     def __lt__(self, other):
#         if other.line.y_sorting > self.line.y_sorting:
#             return True
#         elif other.line.y_sorting < self.line.y_sorting:
#             return False
#         elif other.line.y_sorting > self.line.y_sorting:
#             return True
#         elif other.line.y_sorting < self.line.y_sorting:
#             return False
#         else:
#             right_self = self.line.direction[0] > 0
#             right_other = other.line.direction[0] > 0
#             if right_other > right_self:
#                 return True
#             elif right_other < right_self:
#                 return False
#             elif right_self:
#                 return self.line.direction[0] < other.line.direction[0]
#             else:
#                 return self.line.direction[0] > other.line.direction[0]
#
#
# class BeachLineSorter:
#     def __init__(self, line: Line):
#         self.line = line
#         self.y = 0
#
#     def set_y(self, y):
#         self.y = y
#
#     def __lt__(self, other):
#         beach_position_other = other.line.beach_position(self.y)[0]
#         if beach_position_other > self.line.x_sorting:
#             return True
#         elif beach_position_other < self.line.x_sorting:
#             return False
#         else:
#             right_self = self.line.direction[0] > 0
#             right_other = other.line.direction[0] > 0
#             if right_other > right_self:
#                 return True
#             elif right_other < right_self:
#                 return False
#             elif right_self:
#                 return self.line.direction[0] < other.line.direction[0]
#             else:
#                 return self.line.direction[0] > other.line.direction[0]