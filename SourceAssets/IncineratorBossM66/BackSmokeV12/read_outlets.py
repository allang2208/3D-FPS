"""Locate the existing four vent rims on the accepted V10 source mesh."""
import bpy,json,numpy as np
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/BackSmokeV12')
(ROOT/'Records').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'ThumbDrapeV10/Authoring/M66_thumb_drape_v10.blend'))
mesh=bpy.data.objects['M66_Body'];rig=bpy.data.objects['M66_Rig'];p=np.array([v.co[:] for v in mesh.data.vertices])
out=[]
for label in ('High','Rear','Front','Lateral'):
    name='M66_Vent_'+label+'_Tip';bone=rig.data.bones[name];group=mesh.vertex_groups[name].index
    ids=[v.index for v in mesh.data.vertices if any(g.group==group and g.weight>.4 for g in v.groups)]
    head=np.array(bone.head_local);axis=np.array(bone.tail_local)-head;axis/=np.linalg.norm(axis)
    points=p[ids];along=(points-head)@axis;rim=points[along>=np.quantile(along,.94)]
    centre=rim.mean(0);centre+=axis*.025
    # Source faces -Y. UE's ForceFrontXAxis conversion is (-Y,-X,Z), in cm.
    ue=[float(-centre[1]*100),float(-centre[0]*100),float(centre[2]*100)]
    out.append({'bone':name,'source_point_m':centre.tolist(),'reference_cs_cm':ue,'rim_samples':len(rim)})
(ROOT/'Records/outlets.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('M66_BACK_OUTLETS '+json.dumps(out),flush=True)
