import bpy,json
from pathlib import Path
O=Path(__file__).parent;src=json.loads((O/'sources.json').read_text());out={}
for k,v in src.items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=v['source']);pts=[o.matrix_world@v.co for o in bpy.context.scene.objects if o.type=='MESH' for v in o.data.vertices]
 out[k]={'min':[min(v[i] for v in pts) for i in range(3)],'max':[max(v[i] for v in pts) for i in range(3)],'objects':[o.name for o in bpy.context.scene.objects if o.type=='MESH']}
(O/'part_bounds.json').write_text(json.dumps(out,indent=2));print('PART_BOUNDS_PASS')
