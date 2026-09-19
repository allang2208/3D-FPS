import bpy,json,math
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;results={}
for key,title in [('vertical','Vertical'),('prism','Prism')]:
 p=O/key;bpy.ops.wm.open_mainfile(filepath=str(p/f'A_M4_{title}_idle.blend'));r=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();f=json.loads((p/'fit_final.json').read_text());G=r.pose.bones['WPN_root'].matrix@Matrix(f['grip_in_root']);Gi=G.inverted();results[key]={'fingers':{b.name:list(b.matrix_basis.to_quaternion().normalized()) for b in r.pose.bones if b.name.endswith('_l') and b.name.startswith(('index','middle','ring','pinky','thumb'))},'hand_rotation':list((Gi@r.pose.bones['hand_l'].matrix).to_quaternion().normalized()),'forearm':list((Gi.to_3x3()@(r.pose.bones['hand_l'].head-r.pose.bones['lowerarm_l'].head)).normalized()),'hand_in_mount':list(Gi@r.pose.bones['hand_l'].head)}
def angular(a,b):return math.degrees(2*math.acos(min(1,abs(sum(x*y for x,y in zip(a,b))))))
finger=max(angular(q,results['prism']['fingers'][n]) for n,q in results['vertical']['fingers'].items());hand=angular(results['vertical']['hand_rotation'],results['prism']['hand_rotation']);fore=math.degrees(math.acos(min(1,sum(x*y for x,y in zip(results['vertical']['forearm'],results['prism']['forearm'])))))
assert finger<.1 and hand<.1 and fore<.1,(finger,hand,fore)
record={'max_finger_rotation_difference_degrees':finger,'hand_rotation_difference_degrees':hand,'forearm_direction_difference_degrees':fore,'profiles':results,'common_hand_overrides':{k:json.loads((O/k/'contact_overrides.json').read_text()) for k in results}}
assert all(not v for v in record['common_hand_overrides'].values());(O/'shared_pose_validation.json').write_text(json.dumps(record,indent=2));print('SHARED_POSE_PASS',finger,hand,fore)
