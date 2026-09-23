"""Adapt accepted AKM grip hands to PKM without replacing PKM reload mechanics."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;R=O.parent;S=R.parent
src=json.loads((S/'A762Meshy20260920/Accessories05/sources.json').read_text())
geo=json.loads((O/'authoring.json').read_text());G=Matrix(geo['grip_transform'])
bpy.context.preferences.filepaths.save_version=0
donors={}
for family in ['vertical','canted','prism','angled']:
 path=Path(src['animations'][family+'/idle']['source'][0]).with_suffix('.blend')
 bpy.ops.wm.open_mainfile(filepath=str(path));d=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
 inv=d.pose.bones['WPN_root'].matrix.inverted()
 donors[family]={'source':str(path),'bones':{b.name:G@inv@b.matrix for b in d.pose.bones if b.name.endswith('_l')}}
bpy.ops.wm.open_mainfile(filepath=str(O/'PKM_Modular_Editable.blend'))
r=bpy.data.objects['PKM_Manny_Rig'];s=bpy.context.scene
def action(a):r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
action(bpy.data.actions['PKM_Game_idle_Wrist12']);s.frame_set(0);bpy.context.view_layer.update()
base={b.name:b.matrix.copy() for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones};parent={b.name:b.parent.name if b.parent else None for b in r.data.bones}
localrest={n:rest[parent[n]].inverted()@m if parent[n] else m.copy() for n,m in rest.items()}
W0=base['WPN_root'];names=[n for n in base if n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky'))]
def frame(axis,normal):
 x=axis.normalized();z=(normal-x*normal.dot(x)).normalized();y=z.cross(x).normalized();return Matrix((x,y,z)).transposed()
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
def ramp(t,a,b):return smooth((t-a)/(b-a))
def mix(a,b,w):
 p,q,sc=a.decompose();p2,q2,sc2=b.decompose();return Matrix.LocRotScale(p.lerp(p2,w),q.slerp(q2,w),sc.lerp(sc2,w))
def bags(a):
 for layer in a.layers:
  for strip in layer.strips:
   yield from strip.channelbags
clips=json.loads((R/'Wrist12/authoring.json').read_text())['actions'];records={}
for family,donor in donors.items():
 target={n:base[n].copy() for n in names};H=W0@donor['bones']['hand_l'];shoulder=base['upperarm_l'].translation.copy()
 oldU=base['lowerarm_l'].translation-shoulder;oldL=base['hand_l'].translation-base['lowerarm_l'].translation;L1=oldU.length;L2=oldL.length
 line=H.translation-shoulder;distance=line.length;axis=line.normalized()
 if distance>(L1+L2)*.97:
  shift=axis*(distance-(L1+L2)*.97);shoulder+=shift;target['clavicle_l'].translation+=shift;distance=(H.translation-shoulder).length
 along=(L1*L1-L2*L2+distance*distance)/(2*distance);height=math.sqrt(max(0,L1*L1-along*along))
 pole=base['lowerarm_l'].translation-shoulder;pole=(pole-axis*pole.dot(axis)).normalized();elbow=shoulder+axis*along+pole*height
 newU=elbow-shoulder;newL=H.translation-elbow;oldPlane=oldU.cross(oldL).normalized();newPlane=newU.cross(newL).normalized()
 for n,oa,na,p in [('upperarm_l',oldU,newU,shoulder),('lowerarm_l',oldL,newL,elbow)]:
  q=frame(na,newPlane)@frame(oa,oldPlane).transposed();target[n]=q.to_4x4()@base[n];target[n].translation=p
 target['hand_l']=H
 for n in names:
  if n.startswith('upperarm_twist_'):target[n]=target['upperarm_l']@base['upperarm_l'].inverted()@base[n]
 Lf=target['lowerarm_l'];Df=Lf.to_3x3()@rest['lowerarm_l'].to_3x3().inverted();Dh=H.to_3x3()@rest['hand_l'].to_3x3().inverted()
 dq=(Dh@Df.inverted()).to_quaternion();ax=newL.normalized();v=Vector((dq.x,dq.y,dq.z));v=ax*v.dot(ax);twist=Quaternion((dq.w,v.x,v.y,v.z));twist.normalize()
 if twist.w<0:twist.negate()
 for suffix,fraction in [('02',.40),('01',.82)]:
  n='lowerarm_twist_'+suffix+'_l';m=Lf@rest['lowerarm_l'].inverted()@rest[n];p=m.translation.copy();m=Quaternion().slerp(twist,fraction).to_matrix().to_4x4()@m;m.translation=p;target[n]=m
 for n in names:
  if n.startswith(('thumb','index','middle','ring','pinky')):target[n]=W0@donor['bones'][n]
 for key,record in clips.items():
  a=bpy.data.actions[f'PKM_Game_{key}_Feed13' if key in ['fire','aim_fire'] else record['action']];action(a);fps=240 if key in ['fire','aim_fire'] else 60;count=round(record['seconds']*fps)
  s.render.fps=60;s.render.fps_base=1;samples=[]
  for f in range(count+1):
   sf=f*60/fps;s.frame_set(int(sf),subframe=sf%1);bpy.context.view_layer.update();samples.append({b.name:b.matrix.copy() for b in r.pose.bones})
  out=a.copy();out.name=f'A_PKM_{family}_{key}';out.use_fake_user=True
  for bag in bags(out):
   for curve in list(bag.fcurves):
    if any(curve.data_path.startswith(f'pose.bones["{n}"]') for n in names):bag.fcurves.remove(curve)
    elif fps!=60:
     for p in curve.keyframe_points:p.co.x*=fps/60;p.handle_left.x*=fps/60;p.handle_right.x*=fps/60
  action(out);s.render.fps=fps;previous={}
  for f,row in enumerate(samples):
   t=f/fps;weight=1-ramp(t,.26,.62)+ramp(t,2.13,2.30) if key.startswith('reload') else 1.
   X=row['WPN_root']@W0.inverted();goal={n:X@m for n,m in target.items()};desired={n:m.copy() for n,m in row.items()}
   for n in names:
    p=parent[n];oldlocal=row[p].inverted()@row[n];newlocal=(goal[p] if p in goal else row[p]).inverted()@goal[n];desired[n]=desired[p]@mix(oldlocal,newlocal,weight)
   for n in names:
    loc,q,sc=(localrest[n].inverted()@desired[parent[n]].inverted()@desired[n]).decompose()
    if n in previous and previous[n].dot(q)<0:q.negate()
    previous[n]=q.copy();b=r.pose.bones[n];b.location=loc;b.rotation_mode='QUATERNION';b.rotation_quaternion=q;b.scale=sc
    for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=f,group=n)
  for bag in bags(out):
   for curve in bag.fcurves:
    if any(curve.data_path.startswith(f'pose.bones["{n}"]') for n in names):
     for p in curve.keyframe_points:p.interpolation='LINEAR'
  s.frame_start=0;s.frame_end=count;s.frame_set(0);bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
  dest=O/'Animations'/family;dest.mkdir(parents=True,exist_ok=True)
  bpy.ops.export_scene.fbx(filepath=str(dest/(out.name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,bake_anim_step=1)
  records[family+'/'+key]={'name':out.name,'seconds':count/fps,'fps':fps,'donor':donor['source']}
  if fps!=60:
   for bag in bags(out):
    for curve in bag.fcurves:
     for p in curve.keyframe_points:p.co.x*=60/fps;p.handle_left.x*=60/fps;p.handle_right.x*=60/fps
  print('PKM14_GRIP_EXPORTED',family,key,flush=True)
 s.render.fps=60;action(bpy.data.actions[f'A_PKM_{family}_idle']);s.frame_start=0;s.frame_end=60;s.frame_set(0)
 bpy.ops.wm.save_as_mainfile(filepath=str(O/f'PKM_{family}_Editable.blend'))
 (O/'animations.json').write_text(json.dumps(records,indent=2))
print('PKM14_GRIP_AUTHORING_COMPLETE',flush=True)
