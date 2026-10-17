"""Author a palm-up fore-end grasp against native skinned surfaces."""
import bpy,json,math,ast,sys,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;P=O.parents[1];PREV=O.parent/'M870GripADS20261016'
code=(PREV/'author_grip.py').read_text().split('tree=ast.parse')[0]
exec(compile(code,str(PREV/'author_grip.py'),'exec'))
# The prior script's source is retained for the whole-arm solver only.
O=Path(__file__).parent
source={n:canonical@idle[n] for n in handbones}
across=(source['index_01_l'].translation-source['pinky_01_l'].translation).normalized()
long=source['middle_01_l'].translation-source['hand_l'].translation
long=(long-across*long.dot(across)).normalized()
normal=long.cross(across).normalized()
targetlong=Vector((.72,.38,.58)).normalized();targetacross=Vector((-.38,.72,0)).normalized();targetnormal=targetlong.cross(targetacross)
rotation=Matrix((targetlong,targetacross,targetnormal)).transposed()@Matrix((long,across,normal)).transposed().inverted()
anchor=Vector((.026,.225,-.796))
delta=Matrix.Translation(anchor)@rotation.to_4x4()@Matrix.Translation(-source['middle_01_l'].translation)
grip={n:delta@m for n,m in source.items()}
base={n:m.copy() for n,m in grip.items()}
# Four phalange chains wrap the actual 44 mm fore-end. Bone centres remain
# outside the shell; final contact is adjusted using the skinned pads.
for digit in ('index','middle','ring','pinky'):
 names=[digit+'_%02d_l'%i for i in (1,2,3)]
 p=base[names[0]].translation.copy();cy=-.7594
 theta=math.atan2(p.z-cy,p.x);radius=math.hypot(p.x,p.z-cy)
 points=[p]
 for i,n in enumerate(names):
  length=(base[names[i+1]].translation-base[n].translation).length if i<2 else {'index':.019,'middle':.022,'ring':.021,'pinky':.018}[digit]
  theta+=2*math.asin(min(.95,length/(2*radius)))
  points.append(Vector((radius*math.cos(theta),p.y,cy+radius*math.sin(theta))))
 oldaxis=base[names[1]].translation-base[names[0]].translation
 oldnext=base[names[2]].translation-base[names[1]].translation
 oldnormal=oldaxis.cross(oldnext).normalized()
 for i,n in enumerate(names):
  srcdir=(base[names[i+1]].translation-base[n].translation) if i<2 else base[n].to_quaternion()@rest[n].to_quaternion().inverted()@(r.data.bones[n].tail_local-r.data.bones[n].head_local)
  q=(basis(points[i+1]-points[i],Vector((0,-1,0)))@basis(srcdir,oldnormal).inverted()).to_quaternion()
  grip[n]=Matrix.LocRotScale(points[i],q@base[n].to_quaternion(),Vector((1,1,1)))
ob=bpy.data.objects['M870_V7'];coords=[];ids=[]
for v in ob.data.vertices:
 if sum(g.weight for g in v.groups if ob.vertex_groups[g.group].name in handbones)>.995:ids.append(v.index)
for n in handbones:
 block=np.zeros((len(ids),4));group=ob.vertex_groups.get(n)
 if group:
  for j,i in enumerate(ids):
   v=ob.data.vertices[i];w=sum(g.weight for g in v.groups if g.group==group.index)
   block[j,:3]=np.array(rest[n].inverted()@v.co)*w;block[j,3]=w
 coords.append(block)
np.savez_compressed(O/'contact_inputs.npz',coords=np.array(coords),initial=np.array([grip[n] for n in handbones]))
(O/'contact_bones.json').write_text(json.dumps({'names':handbones,'parents':parents,'grip':{n:[list(v) for v in m] for n,m in grip.items()}},indent=2))
if '--optimized' in sys.argv:
 solution=json.loads((O/'optimized_grip.json').read_text());grip={n:Matrix(m) for n,m in solution['grip'].items()}
row={n:m.copy() for n,m in idle.items()}
shoulder_anchor=to_scene@Vector((-.22,-.08,-.94))
choices=[]
for deg in range(-180,181,2):
 test={n:m.copy() for n,m in idle.items()};stat=solve(test,math.radians(deg));e=canonical@test['lowerarm_l'].translation
 score=stat['wrist_bend_deg']**2+8*max(0,e.z+.85)**2*1e6+max(0,e.x+.10)**2*1e6+max(0,abs(stat['upper_roll_deg'])-35)**2
 choices.append((score,deg,stat,list(e)))
best=min(choices);stats=solve(row,math.radians(best[1]));print('BEST_LOW_ELBOW',best,flush=True)
for n in rest:
 par=parents[n];local=row[par].inverted()@row[n] if par else row[n]
 lr=rest[par].inverted()@rest[n] if par else rest[n]
 r.pose.bones[n].matrix_basis=lr.inverted()@local
# Clear source animation before evaluating the newly authored pose.
r.animation_data.action=None;bpy.context.view_layer.update()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M870_ContactCandidate.blend'))
(O/'grip_candidate.json').write_text(json.dumps({'grip':{n:[list(v) for v in m] for n,m in grip.items()},'stats':stats,'bones':{n:list(m.translation) for n,m in grip.items()}},indent=2))
print('CONTACT_CANDIDATE',stats,flush=True)
