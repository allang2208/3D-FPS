import bpy,json,math
from pathlib import Path
O=Path(__file__).parent;report={}
for clip in ('reload','reload_empty'):
    bpy.ops.wm.open_mainfile(filepath=str(O.parent/f'AKMReloadPolish20260911/base/A_AKM_{clip}.blend'))
    r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;rows=[]
    for f in range(0,325,12):
        s.frame_set(f);mag=r.pose.bones['WPN_SOCKET_Magazine'].matrix
        H=mag.inverted()@r.pose.bones['hand_l'].matrix;M=r.pose.bones['WPN_root'].matrix.inverted()@mag
        rows.append({'frame':f,'wrist_mag':list(H.translation),'wrist_rotation':list(H.to_quaternion()),
                     'mag_root':list(M.translation),'index':list(r.pose.bones['index_02_l'].matrix_basis.to_quaternion())})
    report[clip]={'fps':s.render.fps,'duration':s.frame_end/s.render.fps,'rows':rows}
(O/'motion_reference.json').write_text(json.dumps(report,indent=2))
