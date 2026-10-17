"""Fit a native standing idle to the same original anatomy and carriage as V07."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
BASE=Path(__file__).resolve().parents[1];P=BASE/'V08AIMovement'
data=json.loads((P/'Motion/native_idle.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(BASE/'V14BareBodyHand/Authoring/NightWarden_BareBody_HandRepair_V14.blend'))
bpy.context.preferences.filepaths.save_version=0
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');body=bpy.data.objects['NW14_CompleteBody_HandRepair']
def matrix(v):return Matrix.LocRotScale(Vector(v['p']),Quaternion((v['q'][3],*v['q'][:3])),Vector(v['s']))
names=list(data['reference']);parent={n:p if p in names else None for n,p in data['parents'].items()}
root=next(n for n in names if parent[n] is None);ref={n:matrix(v) for n,v in data['reference'].items()}
local_ref={n:matrix(v) for n,v in data['reference_local'].items()};inv_ref={n:m.inverted() for n,m in ref.items()}
def depth(n):return depth(parent[n])+1 if parent[n] else 0
ordered=sorted(names,key=depth)
def ancestors(n):
 out=[]
 while parent[n]:n=parent[n];out.append(n)
 return out
descendants={n:[b for b in ordered if b==n or n in ancestors(b)] for n in ordered}
rows=[]
for row in data['frames']:
 world={n:matrix(v) for n,v in row.items()};neutral=ref[root]@world[root].inverted();rows.append({n:neutral@m for n,m in world.items()})
center=sum((r['Bone_001'].translation for r in rows),Vector())/len(rows)
offset=ref['Bone_001'].translation-center;offset.z=0
C=Matrix(((0,-100,0,0),(-100,0,0,0),(0,0,100,0),(0,0,0,1)));invC=C.inverted()
groups={g.index:g.name for g in body.vertex_groups};samples=[]
for family in [{'Bone_008','Bone_007','Bone_006'},{'Bone_013','Bone_012','Bone_011'}]:
 foot=[]
 for v in body.data.vertices:
  weights={groups[g.group]:g.weight for g in v.groups if groups[g.group] in ref and g.weight>1e-6}
  if sum(weights.get(n,0) for n in family)>.6:foot.append((body.matrix_world@v.co,weights))
 limit=float(np.percentile([p.z for p,w in foot],10))+.008
 foot=[(C@p,w) for p,w in foot if p.z<=limit];samples.extend(foot[::max(1,math.ceil(len(foot)/160))])
def rotate(pose,n,axis,degrees):
 point=pose[n].translation;M=Matrix.Translation(point)@Quaternion(axis,math.radians(degrees)).to_matrix().to_4x4()@Matrix.Translation(-point)
 for b in descendants[n]:pose[b]=M@pose[b]
def ground(pose):
 deform={n:pose[n]@inv_ref[n] for n in names};height=[]
 for p,weights in samples:
  total=sum(weights.values());v=sum(((deform[n]@p)*(w/total) for n,w in weights.items()),Vector());height.append(v.z)
 shift=Vector((0,0,.30-min(height)))
 for n in names:
  if n!=root:pose[n].translation+=shift
for pose in rows:
 for n in names:
  if n!=root:pose[n].translation+=offset
 for n,degrees in [('Bone_022',-4.),('Bone_027',6.)]:rotate(pose,n,(1,0,0),degrees)
 for n,degrees in [('Bone_021',-4.),('Bone_026',-8.)]:rotate(pose,n,(0,1,0),degrees)
 ground(pose)
# Close the existing quiet idle over its last quarter second, retaining feet
# and the original reference-local bone bases instead of a frozen walk pose.
locals=[{n:pose[parent[n]].inverted()@pose[n] if parent[n] else ref[n].copy() for n in names} for pose in rows]
fade=min(8,len(locals)-1)
for i in range(len(locals)-fade,len(locals)):
 a=(i-(len(locals)-fade))/(fade-1);a=a*a*(3-2*a)
 for n in names:
  x,y=locals[i][n],locals[0][n];locals[i][n]=Matrix.LocRotScale(x.translation.lerp(y.translation,a),x.to_quaternion().slerp(y.to_quaternion(),a),local_ref[n].to_scale())
keys={n:[] for n in names};last={};poses=[]
for local in locals:
 pose={}
 for n in ordered:pose[n]=pose[parent[n]]@local[n] if parent[n] else ref[n].copy()
 ground(pose);poses.append(pose)
 for n in names:
  m=pose[parent[n]].inverted()@pose[n] if parent[n] else ref[n];p,q,s=m.decompose()
  if n in last and q.dot(last[n])<0:q.negate()
  last[n]=q.copy();keys[n].append({'p':list(p),'q':[q.x,q.y,q.z,q.w],'s':list(local_ref[n].to_scale())})
(P/'Motion/idle_keys.json').write_text(json.dumps({'fps':30,'frames':len(rows),'keys':keys}),encoding='utf-8')
rig.animation_data_clear();rig.animation_data_create();action=bpy.data.actions.new('A_NightWarden_StandingIdle_V08');rig.animation_data.action=action
rest={b.name:rig.matrix_world@b.matrix_local for b in rig.data.bones};last={}
for i,pose in enumerate(poses,1):
 desired={n:invC@pose[n]@inv_ref[n]@C@rest[n] for n in rest}
 for pb in sorted(rig.pose.bones,key=lambda b:len(b.bone.parent_recursive)):
  par=pb.parent;n=pb.name
  basis=pb.bone.convert_local_to_pose(desired[n],pb.bone.matrix_local,parent_matrix=desired[par.name] if par else Matrix.Identity(4),parent_matrix_local=par.bone.matrix_local if par else Matrix.Identity(4),invert=True)
  p,q,s=basis.decompose()
  if n in last and q.dot(last[n])<0:q.negate()
  last[n]=q.copy();pb.rotation_mode='QUATERNION';pb.location=p;pb.rotation_quaternion=q;pb.scale=s
  for channel in ['location','rotation_quaternion','scale']:pb.keyframe_insert(channel,frame=i,group=n)
S=bpy.context.scene;S.render.fps=30;S.frame_start=1;S.frame_end=len(rows);S.frame_set(1);action.use_fake_user=True
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Authoring/NightWarden_StandingIdle_V08.blend'))
print('NW8_IDLE_AUTHORED frames='+str(len(rows)),flush=True)
