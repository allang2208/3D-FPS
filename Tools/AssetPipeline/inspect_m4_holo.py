import bpy,json
from pathlib import Path
from mathutils import Vector
out=Path('D:/FPS3D/FPSGAME/SourceAssets/M4Holographic20260909');out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath='D:/FPS3D/FPSGAME/Content/holographicpacked.fbx')
rows=[]
for o in bpy.context.scene.objects:
 if o.type=='MESH':
  pts=[o.matrix_world@v.co for v in o.data.vertices]
  rows.append(dict(name=o.name,bounds=[[min(p[i] for p in pts),max(p[i] for p in pts)] for i in range(3)],materials=[m.name for m in o.data.materials]))
(out/'holo-inspect.json').write_text(json.dumps(rows,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(out/'holo_source.blend'))
