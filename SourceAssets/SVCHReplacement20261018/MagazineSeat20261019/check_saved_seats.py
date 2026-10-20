"""Compare actual imported mesh vertices with the original assembled interfaces."""
from arm_math import *
from scipy.spatial import cKDTree
import trimesh

installed=json.load(gzip.open(O/'installed_geometry.json.gz','rt'))
source=json.load(gzip.open(O/'magazine_geometry.json.gz','rt'))
p=pose('idle',0);r=ids['WPN_root'];m=ids['WPN_SOCKET_Magazine'];ref=matrices(weapon['reference'])
neutral=np.linalg.inv(p[r]@np.linalg.inv(ref[r]))@p[m]
report={'runtime_tested':False,'saved_mesh_readback':True,'magazines':{}}
for name,mesh in installed.items():
    actual=np.asarray(mesh['positions']);expected=np.asarray(source[name]['socket_cm'])
    a,_=cKDTree(expected).query(actual);b,_=cKDTree(actual).query(expected)
    fitted=transform(neutral,actual*.01)
    target=np.asarray(source[name]['visual_component_cm'])
    c,_=cKDTree(target).query(fitted);d,_=cKDTree(fitted).query(target)
    row={'path':mesh['path'],'materials':mesh['materials'],'saved_socket_vertex_error_cm':float(max(a.max(),b.max())),'assembled_vertex_error_cm':float(max(c.max(),d.max())),'assembled_bounds_cm':[fitted.min(0).tolist(),fitted.max(0).tolist()]}
    if row['assembled_vertex_error_cm']>.002:raise RuntimeError(('Imported magazine does not match assembly',name,row))
    report['magazines'][name]=row
# The original alternate is a different shell. Compare surfaces at its actual
# shared upper feed interface rather than requiring identical vertex topology.
a=np.array(source['Magazine10']['visual_component_cm']);b=np.array(source['Magazine20']['visual_component_cm'])
neck=a[a[:,2]>a[:,2].max()-3.]
_,dist,_=trimesh.proximity.closest_point(trimesh.Trimesh(b,source['Magazine20']['triangles'],process=False),neck)
report['original_alternate_upper_surface_q95_cm']=float(np.quantile(dist,.95))
report['complete']=True
(O/'seat_check.json').write_text(json.dumps(report,indent=2));print('SVCH_SAVED_SEATS',json.dumps(report),flush=True)
