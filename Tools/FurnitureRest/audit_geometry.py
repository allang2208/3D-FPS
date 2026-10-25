"""Sample skinned body against every configured furniture mesh and slot."""
import sys,json,math
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(sys.argv[sys.argv.index('--root')+1]) if '--root' in sys.argv else Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/RefineV2')
saved='--saved' in sys.argv
full_rate='--full-rate' in sys.argv
only=sys.argv[sys.argv.index('--only')+1] if '--only' in sys.argv else None
config_path=Path(sys.argv[sys.argv.index('--config')+1]) if '--config' in sys.argv else ROOT/'furniture_rest.json'
sys.argv=['audit','--',('--v2' if saved else '--candidate'),'--review',str(ROOT/('ReviewSaved' if saved else 'Audit'))]
sys.argv.extend(['--config',str(config_path)])
code=Path('D:/FPS3D/FPSGAME/Tools/FurnitureRest/render_review.py').read_text()
exec(code[:code.index('bpy.ops.wm.read_factory_settings')])
ROOT=ROOT.parent
GEOMETRY=ROOT/'Geometry' if (ROOT/'Geometry/index.json').exists() else ROOT.parent/'RefineV2/Geometry'
index=json.loads((GEOMETRY/'index.json').read_text())
config=json.loads(config_path.read_text(encoding='utf-8'))
dominant=np.array([geo['bone_names'][max(ws,key=lambda x:x[1])[0]] if ws else 'none' for ws in geo['weights']])
ids=np.arange(0,len(points),4)
support_ids=np.array([i for i,ws in enumerate(headgeo.get('weights',[])) if sum(weight for b,weight in ws if headgeo['bone_names'][b]=='head')>.9])[::8] if head_influences else np.arange(0,len(headpoints),20)
cache={}
for kind in config['types']:
 if only and not kind.startswith(only):continue
 if 'Rest.'+kind+'.Enter' not in rig['clips']:continue
 samples=[]
 for phase in ('Enter','Idle','Exit'):
  data=rig['clips'][f'Rest.{kind}.{phase}'];a=np.array(data['frames'])
  step=1 if full_rate and phase!='Idle' else max(1,round((len(a)-1)/data['duration']/(2 if phase=='Idle' else 10)))
  for j in sorted(set(list(range(0,len(a),step))+[len(a)-1])):
   f=a[j]
   h=skinhead(f)
   samples.append((phase,j*data['duration']/(len(a)-1),skin(f)[ids],h[::20],h[support_ids] if phase=='Idle' and j==0 else None))
 cache[kind]=samples
rows=[]
directions=[Vector(v).normalized() for v in ((1,.37,.21),(-.22,1,.41),(.31,-.18,1))]
def inside(tree,p):
 votes=0
 for direction in directions:
  origin=Vector(p);hits=0
  for _ in range(64):
   loc,_,_,_=tree.ray_cast(origin,direction,1000)
   if loc is None:break
   hits+=1;origin=loc+direction*.003
  votes+=hits%2
 return votes>=2
for profile in config['furniture']:
 if only and not profile['slots'][0]['kind'].startswith(only):continue
 if profile['slots'][0]['kind'] not in cache:continue
 path=profile['mesh'];g=json.loads((GEOMETRY/index[path]).read_text());scale=np.array(profile.get('scale',[1,1,1]));vs=np.array(g['positions'])*scale;ts=np.array(g['triangles'],int)
 bvh=BVHTree.FromPolygons(vs.tolist(),ts.tolist(),all_triangles=True)
 high=Vector([0,0,float(vs[:,2].max()+20)]);loc,n,_,_=bvh.find_nearest(high);normal_sign=1 if n.dot(high-loc)>0 else -1
 for slotnum,slot in enumerate(profile['slots']):
  kind=slot['kind'];seat=np.array(slot['seat'])*scale;seat[2]-=config['types'][kind]['surface_height'];angle=math.radians(slot['yaw']-90);rot=np.array([[math.cos(angle),-math.sin(angle),0],[math.sin(angle),math.cos(angle),0],[0,0,1]])
  worst=[];floor=999;penetrations=0;rest_head=None
  for phase,t,v,hp,skull in cache[kind]:
   v=v@rot.T+seat;hp=hp@rot.T+seat;floor=min(floor,v[:,2].min())
   if phase=='Idle' and t==0:rest_head=skull@rot.T+seat
   for j,p in enumerate(np.vstack([v,hp])):
    loc,n,_,dist=bvh.find_nearest(Vector(p),15)
    if loc is None or dist<.7:continue
    if n.dot(Vector(p)-loc)*normal_sign<-.7 and inside(bvh,p):
     penetrations+=1
     worst.append((float(dist),phase,round(t,3),dominant[ids[j]] if j<len(v) else 'head',p.tolist()))
  gaps=[]
  for p in rest_head:
   loc,_,_,_=bvh.ray_cast(Vector(p)+Vector((0,0,25)),Vector((0,0,-1)),60)
   if loc is not None:gaps.append(float(p[2]-loc.z))
  entry=rot@np.array(config['types'][kind]['entry_offset'])+seat
  clearance=min(bvh.find_nearest(Vector([entry[0],entry[1],entry[2]+z]))[3] for z in np.linspace(44,152,37))-42
  by_bone={}
  for depth,phase,time,bone,point in worst:by_bone[bone]=max(by_bone.get(bone,0.),depth)
  row=dict(mesh=path,slot=slotnum,kind=kind,minimum_body_z=float(floor),entry_capsule_geometry_clearance_cm=float(clearance),head_support_gap_cm=min(gaps) if gaps else None,penetrating_samples=penetrations,max_depth_by_bone=by_bone,worst=sorted(worst,reverse=True)[:8])
  rows.append(row);print('CONTACT',path.split('.')[-1],slotnum,kind,'floor',round(floor,2),'headgap',row['head_support_gap_cm'],'penetrations',penetrations,'worst',row['worst'][:1],flush=True)
(ROOT/('geometry_audit_saved.json' if saved else 'geometry_audit.json')).write_text(json.dumps(rows,indent=2))
