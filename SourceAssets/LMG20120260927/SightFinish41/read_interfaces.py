"""User-requested sight/trigger diagnosis on the saved geometry; no rendering."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;poses=json.loads((O/'pose_inputs.json').read_text());F=Matrix.Diagonal((1,-1,1,1))
def pm(t):
 q=t['q'];return F@Matrix.LocRotScale(Vector(t['p']),Quaternion((q[3],q[0],q[1],q[2])),Vector(t['s']))@F
def imported(path):
 old=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(path),use_anim=False);return set(bpy.data.objects)-old
def bvh(v,f):return BVHTree.FromPolygons(v,f,all_triangles=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
rear=Vector(poses['clips']['aim']['bones']['WPN_RearSight']['p']);rear.y*=-1
front=Vector(poses['clips']['aim']['bones']['WPN_FrontSight']['p']);front.y*=-1
eye=rear+(rear-front).normalized()*.42
out={'scope':'saved geometry at source aim/idle; no game or rendered acceptance','rear_aim':list(rear),'front_aim':list(front),'rear_sight':{}}
for label,path in [('before',O/'Exports/Before_RearSight.fbx'),('saved',O/'Exports/After_RearSight.fbx')]:
 obs=imported(path);vs=[];fs=[]
 for ob in obs:
  if ob.type!='MESH' or ob.name.startswith(('UCX_','UBX_','USP_','UCP_')):continue
  ob.data.calc_loop_triangles();offset=len(vs);vs.extend(ob.matrix_world@v.co+Vector((.0008,.04252,.0855)) for v in ob.data.vertices);fs.extend(tuple(i+offset for i in t.vertices) for t in ob.data.loop_triangles)
 tree=bvh(vs,fs);axis=front-eye;hit=tree.ray_cast(eye,axis.normalized(),axis.length)[0]
 blocked=0
 for a in np.linspace(0,np.pi*2,64,endpoint=False):
  target=front+Vector((.008*np.cos(a),0,.008*np.sin(a)));d=target-eye
  if tree.ray_cast(eye,d.normalized(),d.length)[0] is not None:blocked+=1
 out['rear_sight'][label]={'center_ray_blocked':hit is not None,'blocked_ring_samples':blocked,'ring_samples':64,'ring_radius_m':.008}
 for ob in obs:bpy.data.objects.remove(ob,do_unlink=True)
# Read exact original slot indices, then apply the retained trigger idle delta.
obs=imported(O/'Exports/After_Body.fbx');rig=next(o for o in obs if o.type=='ARMATURE');root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local
bindings=json.loads((O/'bindings.json').read_text());slots=list(next(v for k,v in bindings.items() if 'Cover10/' in k));info={}
delta=pm(poses['clips']['idle']['bones']['WPN_Trigger'])@pm(poses['reference']['WPN_Trigger']).inverted()
for ob in obs:
 if ob.type!='MESH':continue
 me=ob.data;me.calc_loop_triangles();xf=root.inverted()@ob.matrix_world
 for label,key in [('receiver','M_LMG201_H39_Receiver'),('guard','M_LMG201_S41_Cover'),('trigger','M_LMG201_Trigger')]:
  faces=[t.vertices[:] for t in me.loop_triangles if slots[t.material_index]==key]
  if not faces:continue
  transform=delta@xf if label=='trigger' else xf;v=[transform@p.co for p in me.vertices];idx=np.unique(np.array(faces));xyz=np.array([v[int(i)][:] for i in idx]);info[label]={'bounds_m':[xyz.min(0).tolist(),xyz.max(0).tolist()],'bvh':bvh(v,faces)}
out['trigger']={'idle_bounds_m':info['trigger']['bounds_m'],'guard_bounds_m':info['guard']['bounds_m'],'mounts':[]}
for y in [-.070,-.021]:
 p=Vector((.008,y,-.02));direction=Vector((0,0,1));rec=info['receiver']['bvh'].ray_cast(p,direction,.08)[0]
 # Last outside hit from above gives the authored shoulder top.
 guard=info['guard']['bvh'].ray_cast(Vector((.008,y,.03)),Vector((0,0,-1)),.08)[0]
 out['trigger']['mounts'].append({'y':y,'receiver_bottom_z':rec.z if rec is not None else None,'shoulder_top_z':guard.z if guard is not None else None,'overlap_m':guard.z-rec.z if rec is not None and guard is not None else None})
(O/'saved_interfaces.json').write_text(json.dumps(out,indent=2));print('S41_SAVED_INTERFACES',json.dumps(out),flush=True)
