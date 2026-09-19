import bpy,math,json,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(OUT))
from preview_setup import setup,render
r,s,drum=setup()
d=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/M4Drum20260909/build.json').read_text());G=Matrix(d['source_to_component']);center=Vector(d['center']);bind=r.data.bones['WPN_SOCKET_Magazine'].matrix_local.copy()
def action(a):
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
def frame(f):s.frame_set(f);bpy.context.view_layer.update()
action(bpy.data.actions['A_M4_HK416_drum_reload']);frame(95)
D=r.pose.bones['WPN_SOCKET_Magazine'].matrix@bind.inverted()@G@Matrix.Translation(center)
fingers=[b.name for b in r.pose.bones if b.name.endswith('_l') and b.name.startswith(('thumb','index','middle','ring','pinky'))]
original={n:r.pose.bones[n].matrix_basis.copy() for n in fingers}
# Open the fingers before fitting the broad grasp, retaining anatomical opposition.
for n in fingers:
 b=r.pose.bones[n];p,q,z=original[n].decompose();q=q.slerp(Quaternion(),.60 if not n.startswith('thumb') else .30);b.matrix_basis=Matrix.LocRotScale(p,q,z)
bpy.context.view_layer.update()
wrist=r.pose.bones['hand_l'].matrix.copy();knuckle=r.pose.bones['middle_01_l'].head
wrist.translation+=D.to_3x3()@(Vector((.008,.094,-.080))-D.inverted()@knuckle)
def arm_to(goal):
 upper=r.pose.bones['upperarm_l'].matrix.copy();fore=r.pose.bones['lowerarm_l'].matrix.copy();old=r.pose.bones['hand_l'].matrix.copy()
 a=upper.translation;b=fore.translation;c=old.translation;target=goal.translation;l1=(b-a).length;l2=(c-b).length;axis=(target-a).normalized();dist=(target-a).length
 if dist>l1+l2-.00001:a+=axis*(dist-l1-l2+.00001);dist=l1+l2-.00001
 pole=b-a-axis*(b-a).dot(axis);pole.normalize();along=(l1*l1-l2*l2+dist*dist)/(2*dist);elbow=a+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
 r.pose.bones['upperarm_l'].matrix=Matrix.LocRotScale(a,(b-upper.translation).rotation_difference(elbow-a)@upper.to_quaternion(),upper.to_scale());bpy.context.view_layer.update()
 r.pose.bones['lowerarm_l'].matrix=Matrix.LocRotScale(elbow,(c-b).rotation_difference(target-elbow)@fore.to_quaternion(),fore.to_scale());bpy.context.view_layer.update()
 r.pose.bones['hand_l'].matrix=goal;bpy.context.view_layer.update()
arm_to(wrist)
targets={'index':(-.026,.047,-.052),'middle':(-.009,.047,-.071),'ring':(.011,.047,-.091),'pinky':(.029,.047,-.111),'thumb':(-.059,.043,-.126)}
hand_mesh=bpy.data.objects['SK_Manny_Arms_Export']
pad_local={}
for digit in targets:
 n=digit+'_03_l';group=hand_mesh.vertex_groups[n].index
 points=[r.data.bones[n].matrix_local.inverted()@hand_mesh.matrix_world@v.co for v in hand_mesh.data.vertices if any(g.group==group and g.weight>.8 for g in v.groups)]
 pad_local[digit]=sum(points,Vector())/len(points)
for digit,point in targets.items():
 goal=D@Vector(point)
 for iteration in range(25):
  for joint in [3,2,1]:
   b=r.pose.bones[f'{digit}_{joint:02}_l'];tip=r.pose.bones[digit+'_03_l'].matrix@pad_local[digit];pivot=b.head.copy();m=b.matrix.copy()
   turn=(tip-pivot).rotation_difference(goal-pivot);turn=Quaternion().slerp(turn,.5)
   b.matrix=Matrix.LocRotScale(pivot,turn@m.to_quaternion(),m.to_scale());bpy.context.view_layer.update()
# A glove has volume beyond its bones; leave clearance for the intermediate pads.
wrist=r.pose.bones['hand_l'].matrix.copy();wrist.translation+=D.to_3x3()@Vector((0,.012,0));arm_to(wrist)
pose={'wrist_in_drum':[list(v) for v in D.inverted()@r.pose.bones['hand_l'].matrix],'fingers':{n:[list(v) for v in r.pose.bones[n].matrix_basis] for n in fingers},'tips':{n:list(D.inverted()@r.pose.bones[n+'_03_l'].tail) for n in ['index','middle','ring','pinky','thumb']}}
# Key the temporary pose so the render helper's frame_set preserves it.
candidate=bpy.data.actions['A_M4_HK416_drum_reload'].copy();candidate.name='GripPoseReview';action(candidate)
for b in r.pose.bones:
 for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=95)
(OUT/'grip_pose.json').write_text(json.dumps(pose,indent=2))
render(r,s,95,OUT/'grip_pose_review.png')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M4_DrumGrip_Pose.blend'))
print('GRIP_POSE_READY',pose['tips'])
