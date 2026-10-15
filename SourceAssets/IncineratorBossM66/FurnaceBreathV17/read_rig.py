import bpy,json,numpy as np
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/FurnaceBreathV17');(ROOT/'Records').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'ThumbDrapeV10/Authoring/M66_thumb_drape_v10.blend'))
rig=bpy.data.objects['M66_Rig'];mesh=bpy.data.objects['M66_Body'];rows=[]
for b in rig.data.bones:
    if not(b.name.startswith('M66_Sac') or b.name in [f'Bone_{i:03d}' for i in range(10)]):continue
    g=mesh.vertex_groups.get(b.name);points=np.array([v.co[:] for v in mesh.data.vertices if g and any(x.group==g.index and x.weight>.4 for x in v.groups)])
    rows.append({'name':b.name,'parent':b.parent.name if b.parent else None,'head':list(b.head_local),'tail':list(b.tail_local),
        'weighted_bounds':[points.min(0).tolist(),points.max(0).tolist()] if len(points) else None})
(ROOT/'Records/rig_anatomy.json').write_text(json.dumps(rows,indent=2));print('M66_BREATH_RIG '+json.dumps(rows))
