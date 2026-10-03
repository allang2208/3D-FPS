"""Locate the installed AKM-family magazine seating from its source bone motion."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent;S=O.parents[2]/'SourceAssets'
auth=json.loads((S/'RifleMagazineGrip20260922/IndexClearanceV4/authoring.json').read_text())
out={}
for key,job in auth.items():
    if job['family']!='base' or job['magazine']!='standard':continue
    path=Path(job['blend'])
    if job['gun']=='A762' and job['clip']=='reload_empty':path=S/'A762RightCharge20260922/base/A_A762_reload_empty.blend'
    bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];end=round(r.animation_data.action.frame_range[1])
    s.frame_set(end);bpy.context.view_layer.update();target=r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones['WPN_SOCKET_Magazine'].matrix
    rows=[]
    for f in range(120,271,2):
        s.frame_set(f);bpy.context.view_layer.update();m=r.pose.bones['WPN_root'].matrix.inverted()@r.pose.bones['WPN_SOCKET_Magazine'].matrix
        rows.append({'frame':f,'distance_mm':(m.translation-target.translation).length*1000,'angle':m.to_quaternion().rotation_difference(target.to_quaternion()).angle})
    out[key]={'source':str(path),'poses':rows}
    print(key,[(v['frame'],round(v['distance_mm'],1)) for v in rows if v['frame']%10==0],flush=True)
(O/'akm_contact_sources.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
