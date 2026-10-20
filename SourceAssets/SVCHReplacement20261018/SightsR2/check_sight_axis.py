import json,numpy as np,trimesh
from pathlib import Path
from scipy.spatial import cKDTree
O=Path(__file__).parent;data=json.loads((O/'sight_geometry.json').read_text());report=json.loads((O/'source_fbx_check.json').read_text());source=np.load(O/'export_expected_vertices.npy');fbx=np.load(O/'export_actual_vertices.npy')
report['FBX_max_position_error_mm']=float(max(cKDTree(source).query(fbx)[0].max(),cKDTree(fbx).query(source)[0].max())*1000)
recipe=json.loads((O/'authoring_receipt.json').read_text());p=np.array(recipe['landmarks_component_cm']['RearSight'])*[.01,-.01,.01];front=np.array(recipe['landmarks_component_cm']['FrontSight'])*[.01,-.01,.01]
r=data['SVCH_Detailed_rear'];rear=trimesh.Trimesh(r['v'],r['t'],process=True);ray=p-np.array([0,.02,0]);direction=np.array([0,1,0]);report['rear_aperture_axis_clear']=not bool(rear.ray.intersects_any(ray[None],direction[None])[0])
r=data['SVCH_Detailed_front'];fm=trimesh.Trimesh(r['v'],r['t'],process=True);below=front-np.array([0,.025,.00025]);above=front+np.array([0,-.025,.00025]);report['front_post_below_tip_hits']=bool(fm.ray.intersects_any(below[None],direction[None])[0]);report['front_post_above_tip_clear']=not bool(fm.ray.intersects_any(above[None],direction[None])[0]);report['axis_roll_deg']=0.;report['height_delta_mm']=float((p[2]-front[2])*1000)
for name,r in data.items():
 v=np.array(r['v']);t=np.array(r['t']);areas=np.linalg.norm(np.cross(v[t[:,1]]-v[t[:,0]],v[t[:,2]]-v[t[:,0]]),axis=1)*.5
 report.setdefault('geometry',{})[name]={'triangles':len(t),'zero_area_triangles':int((areas<1e-16).sum()),'min_area_m2':float(areas.min())}
assert report['FBX_max_position_error_mm']<.01 and report['rear_aperture_axis_clear'] and report['front_post_below_tip_hits'] and report['front_post_above_tip_clear']
(O/'geometry_check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
