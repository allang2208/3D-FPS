import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(O/'PKM_Manny_Reload_Editable.blend'));r=bpy.data.objects['PKM_Manny_Rig'];s=bpy.context.scene
a=bpy.data.actions['PKM_Idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0)
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix']);W=r.pose.bones['WPN_root'].matrix@fit
data=json.loads((R.parent/'MannyGraspDonor20260912/Opening/0.8/aligned_fit.json').read_text());hand=Matrix(data['grip_in_root']).inverted()@Matrix(data['hand_in_root'])
report={'hand_in_grip':[list(row) for row in hand],'bones':{n:list(W.inverted()@r.pose.bones[n].matrix.translation) for n in ['upperarm_l','lowerarm_l','hand_l','thumb_01_l','thumb_02_l','thumb_03_l','index_01_l','index_03_l','middle_01_l','middle_03_l','pinky_01_l','pinky_03_l']}}
(O/'hand_frames.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
