"""Read native hand anatomy needed to author the closed-fist adaptation."""
import bpy,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/FistSlamV14')
(ROOT/'Records').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'GroundSlamV13/Authoring/M66_ground_slam_v13.blend'))
rig=bpy.data.objects['M66_Rig'];mesh=bpy.data.objects['M66_Body']
rows=[]
for n in ['Bone_037','Bone_036']+['Bone_%03d'%i for i in range(54,74)]:
    b=rig.data.bones[n]
    rows.append({'name':n,'parent':b.parent.name,'head':list(b.head_local),'tail':list(b.tail_local)})
(ROOT/'Records/hand_anatomy.json').write_text(json.dumps(rows,indent=2))
print('M66_HAND_ANATOMY '+json.dumps(rows),flush=True)
