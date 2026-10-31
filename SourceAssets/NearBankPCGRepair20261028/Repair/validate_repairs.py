from pathlib import Path
import json,sys,collections,itertools,math
R=Path(__file__).resolve().parent;A=R.parent/'Audit';sys.path.insert(0,str(A/'pythonlib'))
import numpy as np,shapely
from shapely.geometry import Point,MultiPoint,LineString
from shapely.ops import unary_union
from scipy.spatial import cKDTree,ConvexHull
from scipy.spatial.transform import Rotation
saved=json.loads((R/'saved_readback.json').read_text());manifest=json.loads((R/'repaired_manifest.json').read_text());plan=json.loads((R/'repair_plan.json').read_text());baseline=json.loads((A/'saved_scene.json').read_text());B=baseline['meshes']
road=shapely.from_wkb((R/'road.wkb').read_bytes());pads=shapely.from_wkb((R/'pads.wkb').read_bytes());parking=shapely.from_wkb((R/'parking_domain.wkb').read_bytes());park=shapely.from_wkb((A/'park.wkb').read_bytes());walk=shapely.from_wkb((A/'sidewalk.wkb').read_bytes())
def world(v,t):return (np.array(v)@(Rotation.from_quat(t['q']).as_matrix()*np.array(t['s'])[None,:]).T+np.array(t['p']))/100
def fp(mesh,t):
 b=B[mesh];v=world(list(itertools.product(*zip(b['min'],b['max']))),t);return MultiPoint(v[:,:2]).convex_hull,v[:,2].min()
actual=[r for r in saved['rows'] if r['actor'].startswith('NBPCG_')]
expected=collections.defaultdict(list);got=collections.defaultdict(list)
for r in manifest['rows']:expected[r['mesh']].extend(r['transforms'])
for r in actual:got[r['mesh']].extend(r['transforms'])
errors=[];max_transform_error=0
for mesh,trs in expected.items():
 dest=got[mesh]
 if len(dest)!=len(trs):errors.append(['instance_count',mesh,len(trs),len(dest)]);continue
 distance,index=cKDTree(np.array([t['p'] for t in dest])).query(np.array([t['p'] for t in trs]));max_transform_error=max(max_transform_error,float(distance.max()))
 if distance.max()>.1:errors.append(['pose',mesh,float(distance.max())])
for mesh in got:
 if mesh not in expected:errors.append(['extra_mesh',mesh])
ef=[v for r in manifest['rows'] for t in r['transforms'] for v in t.get('custom',[])];af=[v for r in actual for v in r['custom']]
if collections.Counter(round(v,5) for v in ef)!=collections.Counter(round(v,5) for v in af):errors.append(['custom_data_changed'])
obstacles=[];carpolys=[];cars=[];road_heights=[];colliders=collections.Counter();collision_errors=[];low_hulls={}
for r in saved['rows']:
 mesh=r['mesh']
 if '/Repair/Collision/' in mesh:
  colliders[mesh.rsplit('/',1)[-1].split('.')[0]]+=len(r['transforms'])
  if r['profile']!='BlockAll' or r['visible'] or not r['hidden'] or 'CTF_USE_COMPLEX_AS_SIMPLE' not in saved['meshes'][mesh]['collision_trace']:collision_errors.append(mesh)
 if any(k in mesh for k in ['StreetLamp','Parking_Meter','Road_Sign','Hydrant','Mailbox','BlackAlder']) or (r['actor'].startswith('NB28_Cell_') and any(k in mesh for k in ['Tree','Aspen'])):
  b=B[mesh]
  if mesh not in low_hulls:
   vv=np.array(b.get('vertices',[]))
   if len(vv):
    vv=vv[(vv[:,2]>=b['min'][2]-.1)&(vv[:,2]<=b['min'][2]+300)];vv=vv[ConvexHull(vv[:,:2]).vertices]
   low_hulls[mesh]=vv
  vv=low_hulls[mesh]
  for t in r['transforms']:
   if any(k in mesh for k in ['BlackAlder','Tree','Aspen']):p=Point(np.array(t['p'])[:2]/100).buffer(.4)
   elif len(vv):p=MultiPoint(world(vv,t)[:,:2]).convex_hull
   else:p=fp(mesh,t)[0]
   obstacles.append(p)
 if '/Vehicle/' in mesh:
  for t in r['transforms']:poly,z=fp(mesh,t);carpolys.append(poly);cars.append(dict(mesh=mesh,p=t['p'],bottom=z))
 if 'SM_Lane_Car_' in mesh:
  for t in r['transforms']:road_heights.append(t['p'][2]/100+B[mesh]['max'][2]*t['s'][2]/100)
tree=shapely.STRtree(obstacles);car_tree=shapely.STRtree(carpolys)
contacts=[];carcontacts=[];outside=[]
parking_tolerant=parking.buffer(.002);shapely.prepare(parking_tolerant)
for i,p in enumerate(carpolys):
 if not parking_tolerant.covers(p):outside.append(i)
 for j in tree.query(p,predicate='intersects'):
  if p.intersection(obstacles[j]).area>1e-5:contacts.append([i,int(j)])
 for j in car_tree.query(p.buffer(1.09),predicate='intersects'):
  if j>i:carcontacts.append([i,int(j)])
for r in actual:
 if 'BlackAlder' in r['mesh'] and (r['profile']!='BlockAll' or saved['meshes'][r['mesh']]['simple_shapes']==0):collision_errors.append(r['mesh'])
cfg=json.loads((R.parent/'native_inputs.json').read_text());gaps=[]
for x in cfg['inputs']:
 if x['tag'] not in ['NBPCG_Local','NBPCG_Collector','NBPCG_Artery']:continue
 p=np.array(x['points'])[:,:2]/100
 if x['closed']:p=np.vstack([p,p[0]])
 g=LineString(p).difference(road.buffer(.005))
 if g.length>.01:gaps.append(dict(guide=x['name'],missing_m=g.length))
legacytrees=sum(len(r['transforms']) for r in saved['rows'] if r['actor'].startswith('NB28_Cell_') and any(k in r['mesh'] for k in ['Tree','Aspen']))
result=dict(stage='saved_geometry_recheck',native_instances=sum(len(r['transforms']) for r in actual),max_transform_error_cm=max_transform_error,instance_errors=errors,custom_floats_preserved=len(af),parked_cars=len(cars),car_prop_contacts=contacts,car_spacing_errors=carcontacts,cars_outside_parking=outside,car_ground_error_cm=max(abs(c['bottom']+108.37)*100 for c in cars),road_top_range_m=[min(road_heights),max(road_heights)],road_centerline_gaps=gaps,building_pad_road_overlap_m2=pads.intersection(road).area,legacy_trees=legacytrees,collision_errors=collision_errors,collision_instances=dict(colliders),gameplay_run=False,limits=['Geometric layout and saved collision configuration only; no player traversal or driving acceptance run.','Car versus street props uses conservative source-mesh footprints up to 3m, tree trunks use occupancy radii.'])
(R/'geometry_recheck.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='collision_instances'},indent=2))
if errors or contacts or carcontacts or outside or gaps or collision_errors or result['car_ground_error_cm']>.1:raise RuntimeError('Repair recheck has remaining findings')
