"""Export the authored palm trajectory for attack placement/configuration."""
import bpy,json,numpy as np
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/GroundSlamV13')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/M66_ground_slam_v13.blend'))
rig=bpy.data.objects['M66_Rig'];scene=bpy.context.scene
names=['Bone_037','Bone_036']
for root in (57,61,65,69,73):names.extend('Bone_%03d'%n for n in (root,root-2,root-3))
feet=(rig.data.bones['Bone_010'].head_local+rig.data.bones['Bone_015'].head_local)*.5
rows=[]
for frame in range(89,104):
    scene.frame_set(frame);bpy.context.view_layer.update();points=[]
    for name in names:
        p=rig.pose.bones[name].matrix.translation
        points.append([float((-p.y+feet.y)*100),float((-p.x+feet.x)*100),float(p.z*100)])
    rows.append({'time':frame/60,'points_actor_feet_cm':points})
report={'bones':names,'frames':rows}
(ROOT/'Records/contact_authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
p=np.array([r['points_actor_feet_cm'] for r in rows]);low=p[(p[:,:,2]>20)&(p[:,:,2]<180)]
print('M66_SLAM_CONTACT_GEOMETRY '+json.dumps({'player_height_band_min':low.min(0).tolist(),'player_height_band_max':low.max(0).tolist()}),flush=True)
