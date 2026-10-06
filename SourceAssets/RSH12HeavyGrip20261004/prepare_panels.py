"""Author inset palm panels and cosmetic screw clearances for the new grip."""
import json,sys,math
from pathlib import Path
import numpy as np
O=Path(__file__).resolve().parent
sys.path.insert(0,str(O.parent/'RSH12GripSurfaces20261004/.deps'))
from shapely import constrained_delaunay_triangles
from shapely.geometry import Polygon,Point,box
source=json.loads((O.parent/'RSH12GripSurfaces20261004/panel_inputs.json').read_text())
panels=[]
for original in source['panels']:
    native=Polygon(original['source_boundary_yz'])
    # Rounded inset keeps the same host contact surface, while improving the
    # panel outline. The recess is visual only; the shell remains continuous.
    domain=native.buffer(-.0034,quad_segs=10).buffer(.0012,quad_segs=10)
    domain=domain.intersection(Polygon([(.05,-.0666),(.25,-.0596),(.25,.1),(.05,.1)]))
    domain=domain.difference(Point(.151,-.046).buffer(.0032,quad_segs=16))
    y0,z0,y1,z1=domain.bounds
    positions=[];triangles=[];lookup={}
    def vertex(p):
        key=tuple(round(float(v),10) for v in p)
        if key not in lookup:lookup[key]=len(positions);positions.append(list(key))
        return lookup[key]
    for y in np.arange(y0,y1,.0015):
        for z in np.arange(z0,z1,.0015):
            clipped=domain.intersection(box(y,z,y+.0015,z+.0015))
            if clipped.area<1e-12:continue
            for tri in constrained_delaunay_triangles(clipped).geoms:
                pts=list(tri.exterior.coords)[:3]
                a,b,c=np.asarray(pts)
                cross=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
                if abs(cross)<1e-12:continue
                if cross<0:pts.reverse()
                triangles.append([vertex(p) for p in pts])
    panels.append(dict(side=original['side'],positions_yz=positions,triangles_ccw=triangles,
        distance_to_edge=[domain.boundary.distance(Point(p)) for p in positions],
        boundary_yz=list(domain.exterior.coords),holes_yz=[list(r.coords) for r in domain.interiors],
        slope_y_from_z=original['slope_y_from_z']))
(O/'panel_inputs.json').write_text(json.dumps(dict(panels=panels,source='RSH12GripSurfaces20261004 actual palm domains',
    screw_center_yz=[.151,-.046],reason='Rounded inset, lower metal clearance and cosmetic screw relief'),indent=2),encoding='utf8')
print('HEAVY_GRIP_PANELS_AUTHORED',flush=True)
