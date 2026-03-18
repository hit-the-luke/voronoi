import numpy as np
import collections
from . import line as line_module
from . import beach_line as beach_line_module
from . import event_list as event_list_module
from . import event as event_module
import bisect
from plotly import graph_objects as go
import itertools
import copy



def insert_lines_before(next, edges_to_insert):
    previous = next.previous
    for i in range(0, len(edges_to_insert) - 1):
        edges_to_insert[i].next = edges_to_insert[i+1]
        edges_to_insert[i+1].previous = edges_to_insert[i]
    edges_to_insert[0].previous = previous
    previous.next= edges_to_insert[0]
    edges_to_insert[-1].next = next
    next.previous = edges_to_insert[-1]


class MultiPolygonVoronoi:
    def __init__(self, vertices, edges, angle_max=np.pi / 1):
        self.lines = []
        self.out_lines = []
        self.inner_bisectors = []
        self.outer_bisectors = []
        self.vertices = vertices
        self.edges = edges
        self.angle_max = angle_max
        self.dict_of_horizontals = collections.defaultdict(list)
        self.end_points = []
        self.n_loops = []
        self.edge_in_each_loop = []

    def insert_additional_lines(self, do_draw=False):
        loop = list()
        index_loop = 0
        for edge, i in zip(self.edges, itertools.count()):
            loop.append(line_module.OutLine(self.vertices[edge[0]], self.vertices[edge[1]], index_loop))
            if len(loop) > 1:
                loop[-2].next = loop[-1]
                loop[-1].previous = loop[-2]
            if edge[1] < edge[0]:
                loop[-1].next = loop[0]
                loop[0].previous = loop[-1]
                lines_removed = []
                line = loop[0]
                start = True
                line_stop = loop[0]
                # ==== remove collinear lines ====
                while line != line_stop or start:
                    if line.is_parallel(line.next):
                        lines_removed.append(line.next)
                        if line_stop == line.next:
                            line_stop = line.next.next
                        line.next.remove_line()
                    else:
                        line = line.next
                        start = False
                for line in lines_removed:
                    loop.pop(loop.index(line))
                self.lines.extend(loop)
                self.edge_in_each_loop.append(loop[0])
                loop = []
                index_loop += 1
        self.n_loops = index_loop - 1
        lines_extra = []
        for line in self.lines:
            if line.turn_right(line.next):
                new_lines = [
                    line_module.OutLine(line.end_point, line.end_point, line.index_loop, direction=line.direction),
                    line_module.OutLine(line.end_point, line.end_point, line.index_loop, direction=line.next.direction)
                ]
                if line.is_horizontal:
                    new_lines[0].is_forward = True
                insert_lines_before(line.next, new_lines)
                lines_extra.extend(new_lines)
        self.lines.extend(lines_extra)
        event_list = event_list_module.EventList()
        # adding lines at low points and high points \./ or /'\
        for line in self.lines:
            if line.is_horizontal and line.length() > 0:
                y = line.min_y
                index = bisect.bisect(self.dict_of_horizontals[y],
                                      line.start_point[0], key=lambda elem: elem[0])
                self.dict_of_horizontals[y].insert(index, (line.min_x, line))
                index = bisect.bisect(self.dict_of_horizontals[y], line.end_point[0],
                                      key=lambda elem: elem[0])
                self.dict_of_horizontals[y].insert(index, (line.x_max, line))
            if not line.is_forward and line.next.is_forward:
                bisector = line.next.bisector(line)
                if not line.is_horizontal and not line.next.is_horizontal:
                    if bisector.direction[1] < 0:
                        if not line.is_horizontal:
                            new_line1 = line_module.OutLine(line.start_point, line.start_point, line.index_loop, np.array([-1, 0]))
                        else:
                            new_line1 = None
                        if not line.next.is_horizontal:
                            new_line2 = line_module.OutLine(line.start_point, line.start_point, line.index_loop, np.array([-1, 0]))
                        else:
                            new_line2 = None
                        if new_line1 is not None:
                            if new_line2 is not None:
                                new_line1.next = new_line2
                            else:
                                new_line1.next = line.next
                                bisector = line.next.bisector(new_line1)
                            new_line1.previous = line
                        if new_line2 is not None:
                            new_line2.next = line.next
                            line.next.previous = new_line2
                            if new_line1 is not None:
                                new_line2.previous = new_line1
                                line.next = new_line1
                                bisector = new_line2.bisector(new_line1)
                            else:
                                assert line.previous.length() > 0
                                new_line2.previous = line
                                line.next = new_line2
                                bisector = line.bisector(line.previous)
                                line.is_forward = True
                            new_line2.is_forward = True
                        else:
                            if new_line1 is not None:
                                line.next.previous = new_line1
                event_list.append(event_module.NewLineEvent(bisector.start_point, bisector,
                                                            dict_of_horizontals=self.dict_of_horizontals))

        # adding lines at sharp right turning corners
        for first_line in self.edge_in_each_loop:
            this_line = first_line
            next_line = first_line.next
            while True:
                angle_next_line = this_line.angle(next_line)
                if angle_next_line < -self.angle_max:
                    n_insert = int(np.abs(angle_next_line) / self.angle_max)
                    lines_insert = []
                    for i in range(n_insert):
                        factor = (i + 1) / (n_insert + 1)
                        print(factor)
                        angle_this = angle_next_line * factor
                        t = np.array([[np.cos(angle_this), np.sin(angle_this)], [-np.sin(angle_this), np.cos(angle_this)]])
                        direction = np.einsum("ij, i -> j", t, this_line.direction)
                        extra_line = line_module.OutLine(this_line.end_point, this_line.end_point, this_line.index_loop, direction)
                        lines_insert.append(extra_line)
                    insert_lines_before(next_line, lines_insert)
                if next_line == first_line:
                    break
                else:
                    this_line = next_line
                    next_line = this_line.next
        return event_list

    def test_graph(self):
        for ib in self.inner_bisectors:
            other = ib.start_left
            direction = ib.start_left_direction
            if direction == 1:
                if not other.start_right == ib:
                    _ = 1
                if not other.start_right_direction == 1:
                    _ = 1
            else:
                if not other.end_left == ib:
                    _ = 1
                if not other.end_left_direction == 1:
                    _ = 1

            other = ib.start_right
            direction = ib.start_right_direction
            if direction == 1:
                if not other.start_left == ib:
                    _ = 1
                if not other.start_left_direction == 1:
                    _ = 1
            else:
                if not other.end_right == ib:
                    _ = 1
                if not other.end_right_direction == 1:
                    _ = 1



            other = ib.end_right
            direction = ib.end_right_direction
            if direction == 1:
                if not other.start_right == ib:
                    _ = 1
                if not other.start_right_direction == -1:
                    _ = 1
            else:
                if not other.end_left == ib:
                    _ = 1
                if not other.end_left_direction == -1:
                    _ = 1

            other = ib.end_left
            direction = ib.end_left_direction
            if direction == 1:
                if not other.start_left == ib:
                    _ = 1
                if not other.start_left_direction == -1:
                    _ = 1
            else:
                if not other.end_right == ib:
                    _ = 1
                if not other.end_right_direction == -1:
                    _ = 1

    def add_missing_outer_bisectors(self):
        end_points_test = set(elem[0] for elem in self.end_points)
        while 0 < len(self.end_points):
            this_edge, direction = self.end_points.pop(0)
            left = this_edge.left if direction == 1 else this_edge.right
            while True:
                if all(this_edge.start_point == [0.7432254154219369, 3.7627935830777757]) and direction == -1:
                    _ = 0
                if direction == 1:
                    next_edges = ((this_edge.end_left, this_edge.end_left_direction),
                                  (this_edge.end_right, this_edge.end_right_direction))
                else:
                    next_edges = ((this_edge.start_right, this_edge.start_right_direction),
                                  (this_edge.start_left, this_edge.start_left_direction))
                next_edge, next_direction = next_edges[0]
                if next_edge is None:
                    _ = 0
                if next_edge.is_inner_bisector:
                    next_left = next_edge.left if next_direction == 1 else next_edge.right # debug
                    if next_left != left:
                        fig = self.show(do_display=False)
                        next_left.show(fig=fig, name='next_left')
                        left.show(fig=fig, name='left')
                        next_edge.show(fig=fig, name='next_edge')
                        fig.show()
                        _ = 0
                        assert False
                    assert next_left == left # dbug
                    counterpart = next_edges[1][0]
                    if counterpart.is_inner_bisector:
                       counterpart = None
                    point = this_edge.end_point if direction == 1 else this_edge.start_point
                    if left.serial_number == 11:
                        _ = 0
                    if left.length() == 0:
                        new_line = line_module.OutLine(left.end_point, left.end_point, left.index_loop, left.direction)
                        insert_lines_before(left.next, [new_line])
                    else:
                        try:
                            assert left.split_at_closest_point(point)
                        except AssertionError:
                            fig = self.show()
                            left.show(fig=fig)
                            fig.add_scatter(x=[point[0]], y=[point[1]])
                            fig.show()
                            _ = 0
                            left.split_at_closest_point(point)
                            raise
                    if left.bisector_at_end is None:
                        _ = 0
                    left.next.bisector_at_end = left.bisector_at_end

                    left.bisector_at_end.left = left.next
                    outer_bisector_new = line_module.LineBisectorDummy(left, left.next,left.end_point,point,counterpart)
                    left.bisector_at_end = None
                    left.bisector_at_end = outer_bisector_new
                    self.lines.append(left.next)
                    self.outer_bisectors.append(outer_bisector_new)
                    # # set the left outline of the bisector at the end of the new line
                    temp = (this_edge.start_left if direction == 1 else this_edge.end_right)
                    if temp is not None and not temp.is_inner_bisector:
                        temp.left = left.next
                    if direction == 1:
                        this_edge.left = left.next
                    else:
                        this_edge.right = left.next
                elif next_edges[1][0].is_inner_bisector:
                    next_edge, next_direction = next_edges[1]
                    left = next_edge.left if next_direction == 1 else next_edge.right
                else:
                    break
                if next_edge in end_points_test:
                    break
                this_edge = next_edge
                direction = next_direction


    def calc_edge_thicknesses(self):
        graph = collections.defaultdict(list)
        event_list = self.insert_additional_lines()
        event_list.sort()
        beach_line = beach_line_module.BeachLine(event_list, self.lines, self.inner_bisectors, self.outer_bisectors)

        global y_current
        y_current = event_list[0].edge.min_y

        while event_list:
            event = event_list.pop(0)
            beach_line.y_current = event.y
            try:
                event.handle(beach_line, self.outer_bisectors, self.inner_bisectors, event_list, beach_line.y_current,
                             self.end_points)
            except:
                fig = self.show(do_display=False)
                event.show(fig)
                fig.show()
        self.test_graph()
        self.add_missing_outer_bisectors()
        for outer_bisector in self.outer_bisectors:
            outer_bisector.left.bisector_at_end = outer_bisector

    def get_outer_bisectors_by_loop(self):
        bisectors_all_loops = []
        for first_edge in self.edge_in_each_loop:
            edge = first_edge
            loop = [edge.bisector_at_end]
            edge = edge.next
            while edge != first_edge:
                temp = edge.bisector_at_end
                if temp is None:
                    _ = 1
                loop.append(edge.bisector_at_end)
                edge = edge.next
            bisectors_all_loops.append(loop)
        return bisectors_all_loops

    def show(self, fig=None, do_display=True):
        if fig is None:
            fig = go.Figure()
        x, y = [], []
        for edge in self.lines:
            if edge.length() > 0:
                x.append(edge.origin[0])
                x.append(edge.end_point[0])
                y.append(edge.origin[1])
                y.append(edge.end_point[1])
                x.append(None)
                y.append(None)
        fig.add_scatter(x=x, y=y, line_color='rgb(0,0,255)', name='outline')
        x.clear()
        y.clear()
        for edge in self.outer_bisectors:
            if edge.length() > 0:
                x.append(edge.start_point[0])
                x.append(edge.end_point[0])
                y.append(edge.start_point[1])
                y.append(edge.end_point[1])
                x.append(None)
                y.append(None)
        fig.add_scatter(x=x, y=y, line_color='rgb(0,255,0)', name='outer_bisectors')
        x.clear()
        y.clear()
        for edge in self.inner_bisectors:
            if edge.length() > 0:
                x.append(edge.start_point[0])
                x.append(edge.end_point[0])
                y.append(edge.start_point[1])
                y.append(edge.end_point[1])
                x.append(None)
                y.append(None)
        fig.add_scatter(x=x, y=y, line_color='rgb(255,0,0)', name='inner_bisectors')
        fig.update_layout(
            #         margin=dict(l=0, r=0, b=0, t=0),
            xaxis=dict(scaleanchor="y", scaleratio=1),
            #         yaxis=dict(range=[-10**-15, 10**-15])
        )
        if do_display:
            fig.show()
        return fig
