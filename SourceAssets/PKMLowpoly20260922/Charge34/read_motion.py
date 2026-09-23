import bpy,json
from pathlib import Path
O=Path(__file__).parent;R=O.parent
bpy.ops.wm.open_mainfile(filepath=str(R/'EquipCharge31/PKM_base_EquipCharge_Editable.blend'),use_scripts=False)
r=bpy.data.objects['PKM_Manny_Rig'];s=bpy.context.scene
a=bpy.data.actions['PKM31_base_reload_empty'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
records={}
for t in (4.82,5.00,5.13,5.22,5.35,5.45,5.515,5.55,5.60,5.70,5.90,6.2):
    f=t*120;s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
    inv=r.pose.bones['WPN_root'].matrix.inverted()
    records[str(t)]={n:list((inv@r.pose.bones[n].matrix).translation) for n in ('PKM_Charge','hand_r')}
result={'poses_gun_local':records,'charge_children':[b.name for b in r.data.bones['PKM_Charge'].children_recursive]}
(O/'source_motion.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
