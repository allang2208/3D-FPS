import bpy,json
from mathutils import Vector
from pathlib import Path
O=Path(__file__).parent/'EquipCharge';O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'WalnutFab/AKM_WalnutFab_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
a=bpy.data.actions['AKM_Native_equip'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
rows=[]
for f in range(0,328,12):
 s.frame_set(f);bpy.context.view_layer.update();root=r.pose.bones['WPN_root'].matrix
 rows.append({'frame':f,**{n:list((root.inverted()@r.pose.bones[n].matrix).translation) for n in ['WPN_bolt','WPN_mag','hand_l','hand_r'] if n in r.pose.bones}})
(O/'source_probe.json').write_text(json.dumps(rows,indent=2));print('EQUIP_SOURCE',json.dumps(rows))
code=(O.parent/'review_matched_motion.py').read_text();code=code[code.index("r=bpy.data.objects"):];code=code.replace("cases=[('idle',0)] if '--idle-only' in sys.argv else [('idle',0),('reload',70),('reload',145),('reload_empty',260),('reload_empty',355)]","cases=[('equip',0),('equip',60),('equip',120)]")
exec(compile(code,__file__,'exec'))
