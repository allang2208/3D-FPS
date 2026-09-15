"""Read exported candidate geometry (no rendering or game tests)."""
import bpy,json
from pathlib import Path
p=Path('D:/FPS3D/FPSGAME/SourceAssets/IceSpike20260915')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(p/'SM_SimpleProjectile.fbx'))
rows=[]
for ob in bpy.data.objects:
    if ob.type!='MESH':continue
    rows.append({'name':ob.name,'dimensions':list(ob.dimensions),'vertices':[list(ob.matrix_world@v.co) for v in ob.data.vertices],
                 'triangles':len(ob.data.polygons),'uv_layers':[v.name for v in ob.data.uv_layers]})
(p/'mesh_geometry.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('ICE_SOURCE_GEOMETRY '+json.dumps(rows))
