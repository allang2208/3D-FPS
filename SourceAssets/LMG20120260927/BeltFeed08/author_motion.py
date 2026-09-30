"""Retarget installed accepted PKM reloads; keep phase clock and finger poses."""
import bpy,json,sys,math,importlib.util
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;sys.path.insert(0,str(O))
from feed_lib import *
E=O/'Exports';E.mkdir(exist_ok=True);bpy.context.preferences.filepaths.save_version=0
spec=importlib.util.spec_from_file_location('contact_ik',O.parent.parent/'M4M16ReloadGripFix20260925/grip_lib.py');ik=importlib.util.module_from_spec(spec);spec.loader.exec_module(ik)
d,db,di=load_donor();dr=di['WPN_root'];dl={n:dr.inverted()@m for n,m in di.items()};origin=dl['PKM_Belt_00'].translation
donor_parent={n:v['parent'] for n,v in d['bones'].items()};donor_lr={n:db[p].inverted()@db[n] for n,p in donor_parent.items() if p}
meta=json.loads((O/'geometry_authoring.json').read_text());new_names=set(meta['new_rest'])
bpy.ops.wm.open_mainfile(filepath=str(O/'LMG201_BeltFeed_Editable.blend'),use_scripts=False)
sc=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];sc.render.fps=120;sc.render.fps_base=1;sc.frame_set(0);bpy.context.view_layer.update()
rest={b.name:b.matrix_local.copy() for b in r.data.bones};parent={b.name:b.parent.name if b.parent else None for b in r.data.bones};names=list(rest)
lr={n:rest[parent[n]].inverted()@m if parent[n] else m for n,m in rest.items()}
base={b.name:b.matrix.copy() for b in r.pose.bones};root0=base['WPN_root'];bl={n:root0.inverted()@m for n,m in base.items()}
digits=('thumb_','index_','middle_','ring_','pinky_')
arms=[n for n in names if n.startswith(('clavicle_','upperarm_','lowerarm_','hand_')+digits)]
stations={'lowerarm':0.,'lowerarm_twist_02':.2738694861,'lowerarm_twist_01':.8478689297}
def fingers(n,side):return n.endswith('_'+side) and n.startswith(digits)
def palm_anchor(ps,side):
 h=ps['hand_'+side];f=(ps['middle_01_'+side].translation-h.translation)*.56
 axis=(ps['index_01_'+side].translation-h.translation).cross(ps['pinky_01_'+side].translation-h.translation).normalized()
 if side=='r':axis.negate()
 return h.inverted()@(h.translation+f+axis*.011)
anchor={s:palm_anchor(db,s) for s in ('l','r')}
def read_source(key):
 path=O.parent/'Skin07/Motions'/('A_LMG201_'+key+'.blend')
 with bpy.data.libraries.load(str(path),link=False) as (src,dst):dst.actions=[n for n in src.actions if n=='A_LMG201_'+key+'_Skin07']
 if not dst.actions:raise RuntimeError('Missing current 201 action '+key)
 return dst.actions[0]
def sample_action(action,t):
 assign(r,action);sc.frame_set(int(t*120),subframe=t*120-int(t*120));bpy.context.view_layer.update();return {b.name:b.matrix.copy() for b in r.pose.bones}
source_empty=read_source('reload_empty');charge_samples=[sample_action(source_empty,2.04+(3.52-2.04)*i/300) for i in range(301)]
assign(r,read_source('idle'));sc.frame_set(0);bpy.context.view_layer.update()
def source_charge(t):
 # Accepted 201 pull/stop/return geometry under the accepted PKM event clock.
 keys=[(4.93,2.04),(5.13,2.25),(5.36,2.58),(5.48,2.70),(5.82,350/120),(5.96,3.0),(6.40,3.52)]
 if t<=keys[0][0]:st=keys[0][1]
 elif t>=keys[-1][0]:st=keys[-1][1]
 else:
  st=keys[-1][1]
  for (a,x),(b,y) in zip(keys,keys[1:]):
   if a<=t<=b:st=x+(y-x)*(t-a)/(b-a);break
 pos=max(0,min(300,(st-2.04)/(3.52-2.04)*300));i=int(pos);j=min(300,i+1);w=pos-i
 return {n:charge_samples[i][n].lerp(charge_samples[j][n],w) for n in names}
def copy_track_action(action,key):
 assign(r,action);sc.frame_start=0;sc.frame_end=round(action.frame_range[1]);sc.frame_set(0)
 bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(E/('A_LMG201_'+key+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
def solve_side(p,ref,side,working):
 if working<=1e-8:return p
 rename=lambda n:n[:-2]+'_l' if n.endswith('_'+side) else n+'__other'
 back={rename(n):n for n in names}
 solved=ik.solve_arm(r,[rename(n) for n in names],{rename(n):m for n,m in ref.items()},{rename(n):m for n,m in p.items()})
 p={back[n]:m for n,m in solved.items()}
 up='upperarm_'+side;lo='lowerarm_'+side;hand='hand_'+side
 axis=(p[hand].translation-p[lo].translation).normalized();restaxis=(rest[hand].translation-rest[lo].translation).normalized()
 transport=p[up].to_quaternion()@rest[up].to_quaternion().inverted();zero=(transport@restaxis).rotation_difference(axis)@transport
 q=(p[hand].to_quaternion()@rest[hand].to_quaternion().inverted())@zero.inverted()
 if q.w<0:q.negate()
 theta=2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)
 for stem,station in stations.items():
  n=stem+'_'+side;rot=Quaternion(axis,theta*station)@zero@rest[n].to_quaternion()
  p[n]=Matrix.LocRotScale(p[n].translation,p[n].to_quaternion().slerp(rot,working),p[n].to_scale())
 return p
def mapped_hand(local,side):
 h=local['hand_'+side].copy();a=h@anchor[side];h.translation=map_point(a,origin)-h.to_3x3()@anchor[side];return h
def cover_frame(local):
 rotation=local['PKM_Cover'].to_quaternion()@dl['PKM_Cover'].to_quaternion().inverted()
 return Matrix.LocRotScale(HINGE,rotation,Vector((1,1,1)))
def cover_hand(local,side,reference,target_closed_point):
 h=local['PKM_Cover'].inverted()@local['hand_'+side]
 ref=reference['PKM_Cover'].inverted()@reference['hand_'+side]
 old_anchor=ref@anchor[side]
 wanted=Vector(target_closed_point)-HINGE
 h.translation+=wanted-old_anchor
 return cover_frame(local)@h
report={'revision':'BeltFeed08','donor':'currently installed and user-accepted PKM reloads; COMPRESSED poses at 120 Hz','animations':{},'runtime_tested':False,'visual_tested':False,'normal_seconds':6.5,'empty_seconds':6.6,'original_201_actions':'Skin07'}
for key in json.loads((O.parent/'Skin07/motion_authoring.json').read_text())['animations']:
 a=read_source(key);a.name='A_LMG201_'+key+'_BeltFeed08';copy_track_action(a,key)
 report['animations'][key]={'fps':120,'seconds':sc.frame_end/120,'source':'Skin07 unchanged motion; private mechanical bones stay closed'}
 print('201_BELT_BASE_EXPORTED',key,flush=True)
for key in ('reload','reload_empty'):
 clip=d['clips'][key];empty=key.endswith('empty');outkey='reload_belt_empty' if empty else 'reload_belt';count=len(clip['poses']);samples=[]
 refopen=local_pose(clip['poses'][round(.65*120)])[1];close_t=4.82 if empty else 5.72;refclose=local_pose(clip['poses'][round(close_t*120)])[1]
 right_start=1.4 if empty else 2.3;left_end=1.4 if empty else 2.3;duration=(count-1)/120
 for i,row in enumerate(clip['poses']):
  t=i/120;donorroot,local=local_pose(row);root=root0@dr.inverted()@donorroot
  p={n:root@bl[n] for n in names};p['WPN_root']=root
  for n in names:
   if n in new_names and n!='LMG201_Cover':
    dn=n.replace('LMG201_','PKM_');p[n]=root@map_frame(local[dn],origin)
  p['LMG201_Cover']=root@cover_frame(local)
  for side in ('l','r'):
   active=(ramp(t,.26,.55)*(1-ramp(t,left_end-.20,left_end)) if side=='l' else ramp(t,right_start,right_start+.22)*(1-ramp(t,6.12 if empty else 5.90,6.40 if empty else 6.30)))
   if active<1e-8:continue
   target=mapped_hand(local,side)
   if side=='l':
    cw=ramp(t,.36,.65)*(1-ramp(t,.94,1.28));cover=cover_hand(local,side,refopen,(.027,-.103,.073))
   else:
    begin=4.28 if empty else 5.18;contact=4.35 if empty else 5.25
    cw=ramp(t,begin,contact)*(1-ramp(t,close_t,close_t+.18));cover=cover_hand(local,side,refclose,(.0008,-.151,.078))
   target=target.lerp(cover,cw);target=bl['hand_'+side].lerp(target,active)
   ref={n:m.copy() for n,m in p.items()}
   # Retain the donor's elbow path as IK reference, with the native 201 lengths.
   for n in arms:
    if not n.endswith('_'+side) or n not in local:continue
    m=bl[n].copy();m.translation+=(local[n].translation-dl[n].translation)*active
    m=Matrix.LocRotScale(m.translation,bl[n].to_quaternion().slerp(local[n].to_quaternion()@dl[n].to_quaternion().inverted()@bl[n].to_quaternion(),active),bl[n].to_scale())
    ref[n]=root@m;p[n]=ref[n].copy()
   up='upperarm_'+side;lo='lowerarm_'+side;hand='hand_'+side
   L1=(base[lo].translation-base[up].translation).length;L2=(base[hand].translation-base[lo].translation).length
   ref[lo].translation=ref[up].translation+(ref[lo].translation-ref[up].translation).normalized()*L1
   ref[hand].translation=ref[lo].translation+(ref[hand].translation-ref[lo].translation).normalized()*L2
   p[hand]=root@target
   for n in names:
    if fingers(n,side):
     dn=donor_parent[n];delta=donor_lr[n].inverted()@(local[dn].inverted()@local[n]);newlocal=lr[n]@delta
     baseline=base[parent[n]].inverted()@base[n];p[n]=p[parent[n]]@baseline.lerp(newlocal,active)
   p=solve_side(p,ref,side,active)
  if empty and t>=4.93:
   cp=source_charge(t);cr=cp['WPN_root'];amount=ramp(t,4.93,5.08)
   for n in names:
    if n.endswith('_r') and n.startswith(('clavicle_','upperarm_','lowerarm_','hand_')+digits):p[n]=p[n].lerp(root@cr.inverted()@cp[n],amount)
    if n in ('WPN_ChargingHandle','WPN_BoltCatch'):p[n]=root@cr.inverted()@cp[n]
  # Source-to-idle handoffs are inherited with a short native endpoint blend.
  endblend=ramp(t,duration-.16,duration)
  if endblend>0:
   for n in arms:p[n]=p[n].lerp(root@bl[n],endblend)
  samples.append({n:lr[n].inverted()@(p[parent[n]].inverted()@p[n] if parent[n] else p[n]) for n in names})
 a=bpy.data.actions.new('A_LMG201_'+outkey+'_BeltFeed08');assign(r,a)
 # Create the slotted action through one native insert, then author dense tracks.
 r.pose.bones['WPN_root'].keyframe_insert(data_path='location',frame=0)
 bag=a.layers[0].strips[0].channelbags[0]
 for c in list(bag.fcurves):bag.fcurves.remove(c)
 for n in names:
  rows=[];last=None;r.pose.bones[n].rotation_mode='QUATERNION'
  for s in samples:
   loc,q,scale=s[n].decompose()
   if last is not None and last.dot(q)<0:q.negate()
   last=q.copy();rows.append((tuple(loc),tuple(q),tuple(scale)))
  for prop,num,col in [('location',3,0),('rotation_quaternion',4,1),('scale',3,2)]:
   for j in range(num):
    c=bag.fcurves.new(data_path='pose.bones["'+n+'"].'+prop,index=j);c.keyframe_points.add(count);coords=[]
    for i,v in enumerate(rows):coords.extend((i,v[col][j]))
    c.keyframe_points.foreach_set('co',coords)
    for k in c.keyframe_points:k.interpolation='LINEAR'
    c.update()
 a.use_fake_user=True;copy_track_action(a,outkey)
 report['animations'][outkey]={'fps':120,'seconds':duration,'donor_asset':clip['asset'],'frames':count,'method':'accepted PKM phase/finger motion; object-local 201 cover/box/belt contacts; Skin07 forearm distribution; existing 201 charging tail'}
 print('201_BELT_RELOAD_EXPORTED',outkey,count,flush=True)
for label,t in [('CoverOpen',.65),('OldBeltLift',1.65),('BoxOut',2.6),('BoxSeat',4.35),('BeltSeat',5.1),('CoverClose',5.72)]:sc.timeline_markers.new(label,frame=round(t*120))
assign(r,next(a for a in bpy.data.actions if a.name=='A_LMG201_idle_BeltFeed08'));sc.frame_start=0;sc.frame_end=5;sc.frame_set(0);bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_BeltFeed_Animated.blend'))
(O/'motion_authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
# One extended weapon mesh; the installer copies the actual native UE arms in.
r.data.pose_position='REST';copies=[]
for ob in list(sc.objects):
 if ob.type=='MESH' and ob.parent==r and ob.name.startswith('LMG201_') and 'BareArms' not in ob.name:
  cp=ob.copy();cp.data=ob.data.copy();sc.collection.objects.link(cp);copies.append(cp)
bpy.ops.object.select_all(action='DESELECT')
for ob in copies:ob.hide_set(False);ob.select_set(True)
bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();joined=bpy.context.object;joined.name='LMG201_BeltFeed_Surface'
bpy.ops.object.select_all(action='DESELECT');joined.select_set(True);r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(E/'SK_LMG201_BeltFeed.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
print('201_BELTFEED_MOTION_AND_SURFACE_COMPLETE',flush=True)
