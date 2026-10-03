import bpy,json,ast,sys,itertools,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;sys.path.insert(0,str(O));from motion import Motion
S=O.parent;D=O/'Animations';D.mkdir(exist_ok=True);bpy.context.preferences.filepaths.save_version=0
previous=json.loads((S/'SVDChargeGrip20260924/authoring.json').read_text());data=json.loads((O/'inputs.json').read_text())
tree=ast.parse((S/'SVDCompletion20260923/author_svd.py').read_text(encoding='utf-8-sig'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['sample','select']],type_ignores=[]),'<helpers>','exec'))
def curves(a):return {(c.data_path,c.array_index):c for l in a.layers for s in l.strips for b in s.channelbags for c in b.fcurves}
class Surface:
 def __init__(self,rest):
  skin=data['skin'];self.groups={};self.ids=next(r['vertices'] for r in skin['boundaries'] if 'clavicle_r' in r['weights'])
  points=np.array([[*skin['vertices'][i],1] for i in self.ids]);names={n for i in self.ids for n in skin['weights'][i]}
  for n in names:
   weights=np.array([skin['weights'][i].get(n,0)/sum(skin['weights'][i].values()) for i in self.ids]);self.groups[n]=(points@np.linalg.inv(np.array(rest[n])).T,weights)
  ids=[i for i,w in enumerate(skin['weights']) if sum(v for n,v in w.items() if n.endswith('_r') and n.startswith(('upperarm','lowerarm')))/max(1e-8,sum(w.values()))>.9]
  pts=np.array([[*skin['vertices'][i],1] for i in ids]);self.arm={}
  for n in {n for i in ids for n in skin['weights'][i]}:
   weights=np.array([skin['weights'][i].get(n,0)/sum(skin['weights'][i].values()) for i in ids]);active=weights>0
   self.arm[n]=(np.flatnonzero(active),pts[active]@np.linalg.inv(np.array(rest[n])).T,weights[active])
  self.arm_count=len(ids)
 def error(self,p):
  v=sum((local@np.array(p[n]).T)[:,:3]*w[:,None] for n,(local,w) in self.groups.items());x=v[:,0];depth=v[:,1]+.10;z=v[:,2]-.05
  tv=math.tan(math.radians(82/2));th=tv*16/9
  return min(float(np.max(a)) for a in [depth-.005,th*depth-x,th*depth+x,tv*depth-z,tv*depth+z])+.006
 def clearance(self,p):
  v=np.zeros((self.arm_count,3))
  for n,(ids,local,w) in self.arm.items():v[ids]+=(local@np.array(p[n]).T)[:,:3]*w[:,None]
  v=(np.c_[v,np.ones(len(v))]@np.linalg.inv(np.array(p['WPN_root'])).T)[:,:3]
  worst=0.
  for lo,hi in [(np.array([-.041,-.181,-.003]),np.array([.046,.137,.145])),(np.array([-.020,-.225,-.10]),np.array([.020,.145,.055]))]:
   depth=np.min(np.minimum(v-lo,hi-v),axis=1);worst=max(worst,float(depth.max()))
  return worst
families=['base','vertical','canted','prism','angled'] if '--all' in sys.argv else ['base'];report={};profiles={}
for family in families:
 key=family+'/reload_empty';info=previous[key];bpy.ops.wm.open_mainfile(filepath=info['blend'],use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];scene=bpy.context.scene
 source=bpy.data.actions[info['action']];poses=[sample(r,source,f) for f in range(516)]
 rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones};motion=Motion(poses,rest,parents);surface=Surface(rest)
 candidates=sorted(itertools.product([0.,.04,.08],[.10,.16,.22,.28],[.04,.10,.16,.22]),key=lambda x:x[0]**2+x[1]**2+x[2]**2)
 chosen=None;best=(float('inf'),None)
 for profile in candidates:
  worst=-10
  for f in [248,264,280,310,330,344,388,416,432,464,492]:
   p=motion.pose(f,profile);worst=max(worst,surface.error(p),surface.clearance(p))
   if worst>best[0]:break
  if worst<best[0]:best=(worst,profile)
  if worst<=0:chosen=profile;break
 if chosen is None:chosen=best[1]
 fixed=[motion.pose(f,chosen) for f in range(516)];errors=[surface.error(p) for p in fixed]
 profiles[family]={'back_down_out_m':chosen,'opening_max_m':max(errors[220:516]),'worst_frame':220+int(np.argmax(errors[220:516])),
 'before_opening_max_m':max(surface.error(p) for p in poses[220:516]),'protected_vfov':82,'game_tested':False}
 print('SVD_GRASP_SHOULDER',family,json.dumps(profiles[family]),flush=True)
 action=source.copy();source.name='REFERENCE_REJECTED_AKM_HOOK_'+source.name;action.name=info['name'];action.use_fake_user=True
 original=curves(source);tracks=curves(action)
 for n in motion.edited:
  rows=[(motion.lr[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n])).decompose() for p in fixed]
  for prop,index,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
   path=f'pose.bones["{n}"].{prop}';values=[];last=None
   for f in range(516):
    if 220<f<515:v=rows[f][index].copy()
    elif prop=='rotation_quaternion':v=Quaternion([original[(path,j)].evaluate(f) for j in range(4)])
    else:v=Vector([original[(path,j)].evaluate(f) for j in range(3)])
    if prop=='rotation_quaternion':
     if last is not None and last.dot(v)<0:v.negate()
     last=v.copy()
    values.append(v)
   for j in range(count):
    c=tracks[(path,j)];c.keyframe_points.clear();c.keyframe_points.add(516);c.keyframe_points.foreach_set('co',[v for f,row in enumerate(values) for v in (f,row[j])])
    for k in c.keyframe_points:k.interpolation='LINEAR'
    c.update()
 r.animation_data.action=action;r.animation_data.action_slot=action.slots[0];scene.render.fps=120;scene.render.fps_base=1;scene.frame_start=0;scene.frame_end=515;scene.frame_set(330);bpy.context.view_layer.update()
 blend=O/f'SVD_{family}_Grasp.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend));select([r]);fbx=D/(info['name']+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
 report[key]={**info,'blend':str(blend),'action':action.name,'source':str(fbx),'previous_source':info['source'],'previous_blend':info['blend'],
 'modified_bones':motion.edited,'modified_frames':[221,514],'profile':profiles[family],'changed':'Closed thumb/finger grasp and receiver-outside lower elbow with camera opening protection','game_tested':False}
 (O/'authoring.json').write_text(json.dumps(report,indent=2));(O/'shoulder_profiles.json').write_text(json.dumps(profiles,indent=2))
 if family=='base':(O/'candidate_poses.json').write_text(json.dumps([{n:list(map(list,m)) for n,m in p.items()} for p in fixed]))
 print('SVD_GRASP_AUTHORED',family,flush=True)
