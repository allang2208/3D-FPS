"""Read authoring dimensions needed to cut the replacement garments."""
import bpy, json
import numpy as np
from pathlib import Path
root = Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006')
bpy.ops.wm.open_mainfile(filepath=str(root/'GarmentDrapeV18/BoundCongregate_GarmentDrapeV18.blend'))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
info = {'objects': {}, 'bones': {}, 'torso_slices': []}
for o in bpy.context.scene.objects:
    if o.type != 'MESH': continue
    pts = np.array([v.co[:] for v in o.data.vertices])
    info['objects'][o.name] = dict(vertices=len(pts), bounds=[pts.min(0).tolist(),pts.max(0).tolist()],
        materials=[m.name for m in o.data.materials], matrix=[list(row) for row in o.matrix_world])
for b in rig.data.bones:
    if b.name.startswith('leg_') or b.name in ('body','body_front','body_rear','attack_tentacle_00','attack_tentacle_03'):
        info['bones'][b.name] = dict(head=list(b.head_local),tail=list(b.tail_local))
body=bpy.data.objects['BC_Flesh']
pts=np.array([v.co[:] for v in body.data.vertices if sum(g.weight for g in v.groups if body.vertex_groups[g.group].name in ('body','body_front','body_rear'))>.65])
for z in np.arange(.6,1.81,.15):
    layer=pts[np.abs(pts[:,2]-z)<.04]
    if len(layer):info['torso_slices'].append(dict(z=float(z),bounds=[layer.min(0).tolist(),layer.max(0).tolist()]))
out=root/'GarmentRebuildV19';out.mkdir(exist_ok=True)
(out/'source-dimensions.json').write_text(json.dumps(info,indent=2),encoding='utf8')
print(json.dumps(info),flush=True)
