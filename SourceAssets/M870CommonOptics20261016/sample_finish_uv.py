"""Extract rail surface UV samples from the supplied M870, for material authoring."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O.parent/'M870Tactical20261015/Original/Source/source/M870_Tactical.fbx'),use_anim=False)
uvs=[]
for ob in bpy.context.scene.objects:
    if ob.type!='MESH' or not ob.data.uv_layers.active:continue
    for f in ob.data.polygons:
        p=ob.matrix_world@f.center
        if abs(p.x)<.075 and -.749<p.y<.158 and p.z>.890:
            uv=[ob.data.uv_layers.active.data[i].uv for i in f.loop_indices]
            uvs.append([sum(v.x for v in uv)/len(uv),sum(v.y for v in uv)/len(uv)])
(O/'rail_surface_uv.json').write_text(json.dumps(uvs))
print('M870_RAIL_UV_SAMPLES',len(uvs),flush=True)
