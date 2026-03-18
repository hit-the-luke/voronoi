import test_polygons
from multi_polygon_voronoi.src import multi_polygon_voronoi


for i, polygon in enumerate(test_polygons.all_polygons[1:]):
    vertices, edges = polygon
    calculation = multi_polygon_voronoi.MultiPolygonVoronoi(vertices, edges)
    calculation.calc_edge_thicknesses()
    calculation.get_outer_bisectors_by_loop()
    fig = calculation.show(do_display=False)
    fig.update_layout(title=f'multipolygon {i}')
    fig.show()
    # calc_edge_thicknesses(vertices, edges)

