import numpy as np
from . import line as line_module
import bisect
from . import event as event_module
import plotly.graph_objects as go

class BeachLine(list):
    def __init__(self, event_list, lines, inner_bisectors, outer_bisectors):
        super().__init__()
        self.event_list = event_list
        self.y_current = 0
        self.lines = lines
        self.inner_bisectors = inner_bisectors
        self.outer_bisectors = outer_bisectors

    def insert(self, index, edge):
        assert isinstance(edge, line_module.Line)
        if index > 0 and index < len(self):
            self.event_list.remove([self[index - 1].serial_number, self[index].serial_number])
        if isinstance(edge, line_module.OutLine):
            super().insert(index, edge)
            return
        if index < len(self) and isinstance(self[index - 1], line_module.LineBisector) and np.any(edge.start_point != self[index - 1].start_point):
            intersection_before, k_before = edge.intersection(self[index - 1], return_k=True)
            if edge.k_start_point > k_before:
                k_before = np.inf
        else:
            k_before = np.inf
        if index > 0 and index < len(self) and isinstance(self[index], line_module.LineBisector) and np.any(edge.start_point != self[index].start_point):
            intersection_after, k_after = edge.intersection(self[index], return_k=True)
            if edge.k_start_point > k_after:
                k_after = np.inf
        else:
            k_after = np.inf
        if k_before != np.inf or k_after != np.inf:
            if k_before < k_after:
                intersection = intersection_before
                index_beach = index-1
                k = k_before
                after = False
            else:
                intersection = intersection_after
                index_beach = index
                k = k_after
                after = True
            y_review = edge.y_value(k)
            if after:
                new_event = event_module.IntersectionEvent(y_review, intersection, edge, self[index_beach])
            else:
                new_event = event_module.IntersectionEvent(y_review, intersection, self[index_beach], edge)
            if y_review < self.y_current - 10**-5:
                edge.intersection(self[index - 1], return_k=True)
                raise Exception
            assert y_review >= self.y_current - 10**-5
            self.event_list.insert(new_event)
        super().insert(index, edge)

    def pop(self, index):
        if self[index].serial_number in {1598, 1600, 4221, 4222}:
            print('stoop')
        res = super().pop(index)
        return res

    def remove(self, index_beach):
        if 0 < index_beach < len(self) - 1:
            different_origin = np.any(self[index_beach - 1].origin != self[index_beach + 1].origin)
            all_bisector = (isinstance(self[index_beach - 1], line_module.LineBisector) and
                            isinstance(self[index_beach + 1], line_module.LineBisector))
            if different_origin and all_bisector:
                intersection, k_minus, k_plus = self[index_beach - 1].intersection(self[index_beach + 1],
                                                                                         return_both_k=True)
                if k_minus == np.inf and k_plus == np.inf:
                    return
                y_review = self[index_beach - 1].y_value(k_minus)
                if np.abs(y_review - self[index_beach + 1].y_value(k_plus)) > 10 ** -9:
                    self[index_beach - 1].y_value(k_minus)
                    self[index_beach + 1].y_value(k_plus)
                    print('stop it')
                if not y_review >= self.y_current:
                    self[index_beach - 1].y_value(np.linalg.norm(self[index_beach - 1].origin
                                                                       - intersection))
                intersection_event = event_module.IntersectionEvent(y_review, intersection, self[index_beach - 1],
                                                                    self[index_beach + 1])
                if self[index_beach - 1].direction[1] == -1 or self[index_beach + 1].direction[1] == -1:
                    self.event_list.insert(intersection_event, 0)
                else:
                    self.event_list.insert(intersection_event)

    def show(self, point, y_value=None, do_display=False, limit=None):
        if y_value is None:
            y = point[1]
        else:
            y = y_value
        beach_line_show = np.array([element.beach_position(y) for element in self])
        beach_line_show = np.concatenate([beach_line_show, beach_line_show[:1]])
        beach_line_trend = np.array([element.beach_position(y + 0.2) for element in self])
        beach_line_trend = np.concatenate([beach_line_trend, beach_line_trend[:1]])
        fig = go.Figure()
        x_coords, y_coords = [], []
        for edge in self.lines:
            if edge.length() > 0:
                points_drawn = 0
                if edge.origin[1] < y:
                    x_coords.append(edge.origin[0])
                    y_coords.append(edge.origin[1])
                    points_drawn += 1
                if edge.end_point[1] < y:
                    x_coords.append(edge.end_point[0])
                    y_coords.append(edge.end_point[1])
                    points_drawn += 1
                if points_drawn == 1:
                    bp = edge.beach_position(y)
                    x_coords.append(bp[0])
                    y_coords.append(bp[1])
                if points_drawn > 0:
                    x_coords.append(None)
                    y_coords.append(None)
        fig.add_scatter(x=x_coords, y=y_coords, line_color='rgb(0,0,255)', name='outline')
        x_coords.clear()
        y_coords.clear()
        for edge in self.outer_bisectors:
            if edge.length() > 0:
                x_coords.append(edge.start_point[0])
                y_coords.append(edge.start_point[1])
                if edge.is_done:
                    x_coords.append(edge.end_point[0])
                    y_coords.append(edge.end_point[1])
                else:
                    bp = edge.beach_position(y)
                    x_coords.append(bp[0])
                    y_coords.append(bp[1])
                x_coords.append(None)
                y_coords.append(None)
        fig.add_scatter(x=x_coords, y=y_coords, line_color='rgb(0,255,0)', name='outer_bisectors')
        x_coords.clear()
        y_coords.clear()
        for edge in self.inner_bisectors:
            if edge.length() > 0:
                x_coords.append(edge.start_point[0])
                y_coords.append(edge.start_point[1])
                if edge.is_done:
                    x_coords.append(edge.end_point[0])
                    y_coords.append(edge.end_point[1])
                else:
                    bp = edge.beach_position(y)
                    x_coords.append(bp[0])
                    y_coords.append(bp[1])
                x_coords.append(None)
                y_coords.append(None)
        fig.add_scatter(x=x_coords, y=y_coords, line_color='rgb(255,0,0)', name='inner_bisectors')
        fig.update_layout(
            #         margin=dict(l=0, r=0, b=0, t=0),
            xaxis=dict(scaleanchor="y", scaleratio=1),
            #         yaxis=dict(range=[-10**-15, 10**-15])
        )
        if len(beach_line_show) > 2:
            fig.add_scatter(x=beach_line_show[:, 0] * line_module.FACTOR, y=beach_line_show[:, 1] * line_module.FACTOR,
                            line=dict(color='rgb(255,120,0)'))
            fig.add_scatter(x=beach_line_trend[:, 0] * line_module.FACTOR, y=beach_line_trend[:, 1] * line_module.FACTOR,
                            line=dict(color='rgb(255,120,0)', dash='dash'))
        if fig is not None:
            fig.add_scatter(x=(point[0],), y=(point[1],),
                            marker=dict(size=30, line=dict(color='rgb(255,255,0)', width=1),
                                        color='rgba(0, 0, 0, 0)'))
            fig.update_layout(
                xaxis=dict(scaleanchor="y", scaleratio=1),
            )
            self.event_list.show(fig)
            if do_display:
                fig.show()
        return fig