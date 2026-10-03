import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'Working.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
rows={}
for f in range(270,402,2):
    s.frame_set(f);bpy.context.view_layer.update();root=r.pose.bones['WPN_root'].matrix.inverted()
    rows[f]={n:list((root@r.pose.bones[n].matrix).translation) for n in ('hand_r','WPN_bolt')}
(O/'timing.json').write_text(json.dumps(rows),encoding='utf-8')
print([(f,round(row['WPN_bolt'][1],5)) for f,row in rows.items() if 304<=f<=352],flush=True)
