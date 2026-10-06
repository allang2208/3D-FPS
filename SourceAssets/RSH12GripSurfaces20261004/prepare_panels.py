"""Extract the RSH grip's own lateral boundaries for surface-treatment skins."""
import json, sys
from pathlib import Path
import numpy as np
O=Path(__file__).resolve().parent
sys.path.insert(0,str(O/'.deps'))
from shapely import constrained_delaunay_triangles
from shapely.geometry import Polygon, box, LineString
from shapely.ops import unary_union

source=O.parent/'RSH12Integration20261003/canonical_parts.json'
parts=json.loads(source.read_text(encoding='utf8'))
grip=next(p for p in parts if p['name']=='9_l')
vertices=np.asarray(grip['verts'])
inset=.0008
spacing=.0015
panels=[]

for side in (-1,1):
    polygons=[]; source_faces=[]
    for index,face in enumerate(grip['faces']):
        points=vertices[face]
        normal=np.cross(points[1]-points[0],points[2]-points[0])
        length=np.linalg.norm(normal)
        if length<1e-10:continue
        normal/=length
        # The wide outer palm faces are distinct from the narrow upper neck,
        # backstrap, finger grooves, heel and inward-facing assembly surfaces.
        if normal[0]*side<.94 or np.min(points[:,0]*side)<.0148:continue
        polygon=Polygon(points[:,1:3]).buffer(0)
        if polygon.area>1e-10:
            polygons.append(polygon);source_faces.append(index)
    union=unary_union(polygons)
    regions=list(union.geoms) if union.geom_type=='MultiPolygon' else [union]
    native=max(regions,key=lambda p:p.area)
    domain=native.buffer(-inset,join_style='round',quad_segs=6)
    if domain.is_empty or domain.geom_type!='Polygon':
        raise RuntimeError('RSH palm boundary cannot produce one continuous side skin')
    y0,z0,y1,z1=domain.bounds
    centers=[]
    for z in np.linspace(z0+(z1-z0)*.12,z1-(z1-z0)*.2,28):
        cross=domain.intersection(LineString([(y0-.01,z),(y1+.01,z)]))
        if cross.length>0:centers.append((z,cross.centroid.x))
    slope=float(np.polyfit(np.asarray(centers)[:,0],np.asarray(centers)[:,1],1)[0])
    positions=[];triangles=[];lookup={}
    def vertex(point):
        key=tuple(round(float(v),10) for v in point)
        if key not in lookup:
            lookup[key]=len(positions);positions.append(list(key))
        return lookup[key]
    for y in np.arange(y0,y1,spacing):
        for z in np.arange(z0,z1,spacing):
            clipped=domain.intersection(box(y,z,y+spacing,z+spacing))
            if clipped.area<1e-12:continue
            for triangle in constrained_delaunay_triangles(clipped).geoms:
                points=list(triangle.exterior.coords)[:3]
                a,b,c=(np.asarray(p) for p in points)
                cross=float((b-a)[0]*(c-a)[1]-(b-a)[1]*(c-a)[0])
                if abs(cross)<1e-12:continue
                if cross<0:points.reverse()
                triangles.append([vertex(p) for p in points])
    from shapely.geometry import Point
    distances=[float(domain.boundary.distance(Point(p))) for p in positions]
    panels.append(dict(side=side,positions_yz=positions,triangles_ccw=triangles,
        distance_to_edge=distances,slope_y_from_z=slope,source_faces=source_faces,
        source_boundary_yz=list(native.exterior.coords),boundary_yz=list(domain.exterior.coords),
        holes_yz=[list(r.coords) for r in domain.interiors],clearance_m=inset,
        source_area_m2=native.area,cover_area_m2=domain.area))

(O/'panel_inputs.json').write_text(json.dumps(dict(source=str(source),part='9_l',
    panels=panels,grid_spacing_m=spacing,texture_tile_m=.1,
    selection='Largest actual exterior lateral palm region on each side; inset its native perimeter and holes',
    excludes=['upper neck','backstrap','finger grooves','heel underside','metal frame','mechanical controls']),indent=2),encoding='utf8')
print('RSH_PALM_DOMAINS_AUTHORED',[(p['side'],len(p['positions_yz']),len(p['triangles_ccw'])) for p in panels])
