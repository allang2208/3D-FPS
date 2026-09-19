import bpy,json
from pathlib import Path
root=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(root/'handbrain_detailed_v02.fbx'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
report={'fbx_meshes':len(meshes),'fbx_polygons':sum(len(o.data.polygons) for o in meshes),'fbx_uv_layers':[len(o.data.uv_layers) for o in meshes],'fbx_images':[{'name':i.name,'size':list(i.size),'has_data':i.has_data} for i in bpy.data.images]}
reference=json.loads((root/'model_report.json').read_text())
report['polygon_count_matches']=report['fbx_polygons']==reference['polygons']
report['passed']=bool(meshes) and report['polygon_count_matches'] and all(report['fbx_uv_layers']) and any(i['has_data'] for i in report['fbx_images'])
(root/'export_validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
if not report['passed']: raise RuntimeError('FBX validation failed')
