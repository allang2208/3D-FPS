"""Read the existing M4 toss action and M24 working pose tables; no rendering."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M4TacticalToss20260910/M4_Hand_MAT_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;a=bpy.data.actions['M4_MAT_reload'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
ref={'path':str(O.parent/'M4TacticalToss20260910/M4_Hand_MAT_Editable.blend'),'action':a.name,'fps':s.render.fps,'frames':{},'hand_duties':'right supports rifle; left extracts, opens after toss, retrieves replacement, wraps and seats'}
for f in (8,14,20,24,28,35,43,61,76,95):
 s.frame_set(f);bpy.context.view_layer.update();row={b.name:b.matrix.copy() for b in r.pose.bones};root=row['WPN_root'].inverted()
 ref['frames'][f]={'hand_in_weapon':list(root@row['hand_l'].translation),'mag_in_weapon':list(root@row['WPN_SOCKET_Magazine'].translation),'digits':{n:[math.degrees(v) for v in r.pose.bones[n].matrix_basis.to_quaternion().to_euler('XYZ')] for n in row if n.startswith(('index_','middle_','ring_','pinky_','thumb_')) and n.endswith('_l') and 'metacarpal' not in n}}
(O/'m4_reference.json').write_text(json.dumps(ref,indent=2))
exec(compile((O/'library.py').read_text(),'m24','exec'))
C=Matrix(json.loads((O.parent/'M24Hold20261027/hip-calibration.json').read_text())['hip_transform'])@Matrix.Diagonal((100,-100,100,1))
report={}
for role in ('reload','reload_mag10'):
 report[role]={}
 for f in (18,20,21,22,24,25,26,27,28,29,30,31,32,34,36,38,40):
  row=clips[role][f];cam=C@row['WPN_Magazine']@rest['WPN_Magazine'].inverted()
  report[role][f]={'hand_camera_cm':list(C@row['hand_l'].translation),'mag_center_camera_cm':list(cam@Vector((0,.185,.055 if role=='reload' else .0325))),'mag_in_weapon_m':list(row['WPN_root'].inverted()@row['WPN_Magazine'].translation)}
(O/'working_positions.json').write_text(json.dumps(report,indent=2));print('M24_RELOAD_REFERENCE_READ',flush=True)
