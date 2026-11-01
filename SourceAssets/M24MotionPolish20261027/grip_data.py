import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_MotionPolish_Editable.blend'),use_scripts=False)
r=bpy.data.objects['M24_V9_Rig'];a=bpy.data.actions['A_M24_fire'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(28)
H=r.pose.bones['hand_r'].matrix.inverted();R=r.data.bones['hand_r'].matrix_local.inverted()
for n in ['hand_r']+[f'{f}_{j:02d}_r' for f in ['thumb','index','middle','ring','pinky'] for j in [1,2,3]]:
 b=r.pose.bones[n];rb=r.data.bones[n];print(n,'rest',list(R@rb.head_local),'pose',list(H@b.head),'tail',list(H@b.tail),flush=True)
report=json.loads((O/'authoring.json').read_text());print('knob_in_hand',report['bolt_contact']['contact_hand_local'],flush=True)
print('pn',list(R.to_3x3()@(-(r.data.bones['index_01_r'].head_local-r.data.bones['pinky_01_r'].head_local).cross(r.data.bones['middle_01_r'].head_local-r.data.bones['hand_r'].head_local).normalized())),flush=True)
