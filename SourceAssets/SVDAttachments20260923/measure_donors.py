import bpy,json
from pathlib import Path
O=Path(__file__).parent;src=json.loads((O/'sources.json').read_text());result={}
for key,info in src['meshes'].items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=info['source'][0])
 obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];pts=[o.matrix_world@v.co for o in obs for v in o.data.vertices]
 result[key]={'bounds':{'min':[min(v[i] for v in pts) for i in range(3)],'max':[max(v[i] for v in pts) for i in range(3)]},'objects':[{'name':o.name,'materials':[m.name for m in o.data.materials],'uvs':[x.name for x in o.data.uv_layers]} for o in obs]}
(O/'donor_geometry.json').write_text(json.dumps(result,indent=2))
print('SVD_ATTACH_DONOR_FRAMES_SAVED',flush=True)
