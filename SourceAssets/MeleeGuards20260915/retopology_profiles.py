"""Extract manufacturable quillon profiles from the actual 5080 geometry."""
import sys,json
from pathlib import Path
P=Path(__file__).parent
sys.path.insert(0,str(P/'.authoring-deps'))
import numpy as np,trimesh
from shapely.geometry import Polygon,box,LineString
from shapely.ops import unary_union
from shapely.geometry.polygon import orient
from shapely import polygons,union_all
import mapbox_earcut

for id in ['bastion_guard','riposte_guard','light_guard']:
    source=trimesh.load(P/id/'textured_master_00001_.glb',force='mesh')
    # glTF Y-up -> Blender Z-up, retain X across the guard.
    source.vertices=source.vertices[:,[0,2,1]]*np.array([1,-1,1])
    size=source.extents;center=source.bounds.mean(axis=0)
    span={'bastion_guard':.24,'riposte_guard':.24,'light_guard':.228}[id]
    height={'bastion_guard':.085,'riposte_guard':.115,'light_guard':.074}[id]
    depth={'bastion_guard':.047,'riposte_guard':.042,'light_guard':.040}[id]
    source.vertices=(source.vertices-center)*np.array([span,depth,height])/size
    projected=source.triangles[:,:,[0,2]]
    area=np.abs(np.cross(projected[:,1]-projected[:,0],projected[:,2]-projected[:,0]))
    projected=projected[(area>1e-10)&(projected[:,:,0].max(axis=1)>.004)]
    chunks=[]
    for start in range(0,len(projected),4096):
        chunks.append(union_all(polygons(projected[start:start+4096]),grid_size=.00012))
    # Project the complete surface: a hollow generated shell must not be
    # mistaken for a deliberate hole in the front of the guard.
    shape=union_all(chunks,grid_size=.00012).buffer(.0006,join_style='round').buffer(-.0006,join_style='round').simplify(.00035,preserve_topology=True)
    if shape.geom_type=='MultiPolygon':shape=max(shape.geoms,key=lambda p:p.area)
    # Preserve deliberate lightening holes; fill tiny scan gaps and bastion voids.
    holes=[] if id!='light_guard' else [r.coords[:] for r in shape.interiors if Polygon(r).area>8e-6]
    shape=Polygon(shape.exterior.coords,holes)
    cut=.030
    positive_holes=[Polygon(r).bounds[0] for r in shape.interiors if Polygon(r).bounds[0]>.005]
    if positive_holes:cut=min(cut,min(positive_holes)-.002)
    cross=shape.intersection(LineString([(cut,-1),(cut,1)]))
    if cross.is_empty:raise RuntimeError('Missing generated quillon root: '+id)
    if cross.geom_type!='LineString':
        # A machined root web joins decorative rails before the exact-fit loft.
        z0,z1=cross.bounds[1],cross.bounds[3]
        shape=shape.union(box(cut-.001,z0,cut+.002,z1))
        cross=LineString([(cut,z0),(cut,z1)])
    wing=shape.intersection(box(cut,-1,1,1))
    if wing.geom_type=='MultiPolygon':wing=max(wing.geoms,key=lambda p:p.area)
    if id=='light_guard' and wing.interiors:
        wing=Polygon(wing.exterior.coords,[max(wing.interiors,key=lambda r:Polygon(r).area).coords])
    wing=orient(wing,sign=1)
    loops=[list(wing.exterior.coords)[:-1]]+[list(r.coords)[:-1] for r in wing.interiors]
    vertices=np.array([v for loop in loops for v in loop],dtype=np.float64)
    ends=np.cumsum([len(loop) for loop in loops]).astype(np.uint32)
    triangles=mapbox_earcut.triangulate_float64(vertices,ends).reshape((-1,3))
    data={'source':str(P/id/'textured_master_00001_.glb'),'method':'Orthographic triangle projection of actual generated surface, local contour retopology and precision bevels',
          'vertices_xz':vertices.tolist(),'triangles':triangles.tolist(),'loop_ends':ends.tolist(),
          'cut':cut,'root_z':[cross.bounds[1],cross.bounds[3]],'max_x':wing.bounds[2],
          'hole_count':len(wing.interiors),'source_triangles':len(source.faces)}
    (P/id/'retopology_profile.json').write_text(json.dumps(data,indent=2))
    print('GENERATED_PROFILE',id,'vertices',len(vertices),'holes',len(wing.interiors),'root',data['root_z'],flush=True)
