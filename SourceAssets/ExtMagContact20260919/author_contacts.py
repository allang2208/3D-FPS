"""M4 gets the accepted AKM wrap adapted to its shell; AKM gets a small release.
The magazine owns the contact frame. Fingers retain segment lengths.
"""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;SA=O.parent;preview='--pose' in sys.argv
variants_only='--variants' in sys.argv
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
def handbone(n):return n.endswith('_l') and n.startswith(('hand','thumb','index','middle','ring','pinky'))
def aimed(old,old_end,origin,end):return Matrix.LocRotScale(origin,(old_end-old.translation).rotation_difference(end-origin)@old.to_quaternion(),old.to_scale())
def blend(a,b,w):
 al,aq,az=a.decompose();bl,bq,bz=b.decompose();return Matrix.LocRotScale(al.lerp(bl,w),aq.slerp(bq,w),az)
def open_fingers(p,weight):
 for digit in ['index','middle','ring','pinky']:
  a=digit+'_01_l';b=digit+'_02_l';c=digit+'_03_l'
  axis=(p[b].translation-p[a].translation).cross(p[c].translation-p[b].translation)
  if axis.length<1e-8:continue
  axis.normalize();pivot=p[b].translation;delta=Matrix.Translation(pivot)@Matrix.Rotation(math.radians(-4)*weight,4,axis)@Matrix.Translation(-pivot)
  for n in list(p):
   if n.startswith((digit+'_02',digit+'_03')) and n.endswith('_l'):p[n]=delta@p[n]
 # The small opening is a joint rotation, not translation/scaling of fingers.
bpy.ops.wm.open_mainfile(filepath=str(SA/'AKMReloadPolish20260911/base/A_AKM_reload.blend'))
r=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(148);bpy.context.view_layer.update();W=r.matrix_world.copy();M=W@r.pose.bones['WPN_SOCKET_Magazine'].matrix@r.data.bones['WPN_SOCKET_Magazine'].matrix_local.inverted()@W.inverted()
donor={b.name:M.inverted()@W@b.matrix for b in r.pose.bones if handbone(b.name)}
open_fingers(donor,1.)
params=json.loads((SA/'ExtMagPattern20260919/parameters.json').read_text())
def center(gun,z):
 cy,cz=params[gun]['center_yz'];rad=params[gun]['radius_cm']/100
 return Vector((.0613 if gun=='M4' else .0649,cy-math.sqrt(rad*rad-(z-cz)**2),z))
ca=center('AKM',-.2056);cb=center('M4',-.15)
pa=params['AKM']['center_yz'];pb=params['M4']['center_yz']
angle=math.atan2(cb.z-pb[1],cb.y-pb[0])-math.atan2(ca.z-pa[1],ca.y-pa[0])
alignment=Matrix.Translation(cb)@Matrix.Rotation(angle,4,'X')@Matrix.Translation(-ca)
grasp={n:alignment@p for n,p in donor.items()}
report=json.loads((O/'animation_authoring.json').read_text()) if variants_only and (O/'animation_authoring.json').exists() else {}
jobs=[('M4','reload','M4TacticalToss20260910/M4_Hand_MAT_Editable.blend',126,60,480,(43,61,95,108),76),('M4','reload_empty','M4SlapImpact20260910/M4_Hand_MAT_Editable.blend',162,60,480,(35,43,80,100),54),('AKM','reload','AKMReloadPolish20260911/base/A_AKM_reload.blend',400,120,240,(76,105,178,207),148),('AKM','reload_empty','AKMReloadPolish20260911/base/A_AKM_reload_empty.blend',515,120,240,(90,124,256,286),240)]
if preview:jobs=[x for x in jobs if x[1]=='reload']
if variants_only:
 jobs=[]
 for variant,folder in [('angled','CantedGripMigration20260911/akm/angled'),('vertical','MannyGraspDonor20260912/Final/akm/vertical'),('prism','VREGripExtensions20260912/Final/akm/prism'),('canted','VREGripExtensions20260912/Final/akm/canted')]:
  for clip,end,window,contact in [('reload',400,(76,105,178,207),148),('reload_empty',515,(90,124,256,286),240)]:
   jobs.append(('AKM',clip,folder+'/A_AKM_'+variant+'_'+clip+'.blend',end,120,120,window,contact))
for gun,clip,file,end,fps,rate,window,contact in jobs:
 bpy.ops.wm.open_mainfile(filepath=str(SA/file));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
 if gun=='M4':a=bpy.data.actions['M4_MAT_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 names=[b.name for b in r.pose.bones];parents={b.name:b.parent.name if b.parent else None for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones};lr={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
 W=r.matrix_world.copy();Wi=W.inverted();frames=[contact] if preview else [k*fps/rate for k in range(round(end*rate/fps)+1)];poses=[];maxover=0
 for f in frames:
  s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update();p={b.name:b.matrix.copy() for b in r.pose.bones};original={n:m.copy() for n,m in p.items()}
  weight=smooth((f-window[0])/(window[1]-window[0]))*(1-smooth((f-window[2])/(window[3]-window[2])))
  if weight:
   M=W@p['WPN_SOCKET_Magazine']@rest['WPN_SOCKET_Magazine'].inverted()@Wi
   if gun=='M4':
    target={n:Wi@M@matrix for n,matrix in grasp.items() if n in p}
    p['hand_l']=blend(original['hand_l'],target['hand_l'],weight)
    for n in names:
     if not handbone(n) or n=='hand_l':continue
     parent=parents[n]
     local=original[parent].inverted()@original[n];goal=target[parent].inverted()@target[n]
     loc,q,scale=local.decompose();_,tq,_=goal.decompose()
     p[n]=p[parent]@Matrix.LocRotScale(loc,q.slerp(tq,weight),scale)
   else:
    delta=Wi@M@Matrix.Translation(Vector((-.002,0,0))*weight)@M.inverted()@W
    for n in names:
     if handbone(n):p[n]=delta@p[n]
    open_fingers(p,weight)
   shoulder=original['upperarm_l'].translation;elbow=original['lowerarm_l'].translation;wrist=original['hand_l'].translation;target=p['hand_l'].translation
   l1=(elbow-shoulder).length;l2=(wrist-elbow).length
   # Preserve all bone lengths: let the clavicle rotate before solving elbow.
   if (target-shoulder).length>l1+l2-.004 and 'clavicle_l' in original:
    clav=original['clavicle_l'];c=clav.translation;R=(shoulder-c).length;D=(target-c).length;axis_c=(target-c).normalized()
    cosine=max(-1,min(1,(R*R+D*D-(l1+l2-.004)**2)/(2*R*D)))
    side=shoulder-c-axis_c*(shoulder-c).dot(axis_c);side.normalize()
    newshoulder=c+axis_c*(R*cosine)+side*(R*math.sqrt(max(0,1-cosine*cosine)))
    p['clavicle_l']=aimed(clav,shoulder,c,newshoulder);shoulder=newshoulder
   axis=(target-shoulder).normalized();distance=(target-shoulder).length;maxover=max(maxover,distance-l1-l2)
   distance=min(distance,l1+l2-1e-6);pole=elbow-shoulder-axis*(elbow-shoulder).dot(axis);pole.normalize()
   reach=(l1*l1-l2*l2+distance*distance)/(2*distance);height=math.sqrt(max(0,l1*l1-reach*reach));ne=shoulder+axis*reach+pole*height
   du=aimed(original['upperarm_l'],elbow,shoulder,ne)@original['upperarm_l'].inverted();dl=aimed(original['lowerarm_l'],wrist,ne,target)@original['lowerarm_l'].inverted()
   for n in names:
    if n.endswith('_l') and n.startswith('upperarm'):p[n]=du@original[n]
    elif n.endswith('_l') and n.startswith('lowerarm'):p[n]=dl@original[n]
  poses.append(p)
 variant=next((v+'_' for v in ['angled','vertical','prism','canted'] if '/'+v+'/' in file),'')
 name='A_'+gun+'_ExtContact_'+variant+clip;action=bpy.data.actions.new(name);action.use_fake_user=True;r.animation_data.action=action;previous={}
 for f,p in zip(frames,poses):
  for n in names:
   local=lr[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n]);loc,q,scale=local.decompose()
   if n in previous and previous[n].dot(q)<0:q.negate()
   previous[n]=q.copy();b=r.pose.bones[n];b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=scale
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=f)
 for layer in action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for key in curve.keyframe_points:key.interpolation='LINEAR'
 s.render.fps=fps;s.frame_start=0;s.frame_end=end;s.frame_set(contact)
 bpy.ops.wm.save_as_mainfile(filepath=str(O/(('Pose_' if preview else '')+name+'.blend')))
 if not preview:
  bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
  bpy.ops.export_scene.fbx(filepath=str(O/'FBX'/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=fps/rate,bake_anim_simplify_factor=0)
 report[name]={'source':file,'duration':end/fps,'rate':rate,'contact_window_frames':window,'max_unreachable_m':maxover,'donor':'AKM accepted wrap aligned in magazine coordinates' if gun=='M4' else 'own source with 2 mm palm clearance and 4 degree finger opening'}
 print('AUTHORED_CONTACT',name,flush=True)
(O/('pose_authoring.json' if preview else 'animation_authoring.json')).write_text(json.dumps(report,indent=2))
