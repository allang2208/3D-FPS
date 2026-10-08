import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(P/'Imported_Complete_V3.fbx'))
report=[]
for o in bpy.data.objects:
    if o.type!='MESH':continue
    pts=[o.matrix_world@v.co for v in o.data.vertices]
    report.append({'object':o.name,'vertices':len(pts),'faces':len(o.data.polygons),'world_min':[min(p[k] for p in pts) for k in range(3)],'world_max':[max(p[k] for p in pts) for k in range(3)],'materials':[x.name if x else None for x in o.data.materials]})
(P/'exported_mesh_report.json').write_text(json.dumps(report,indent=2))
print('IMPORTED_UE_FBX',json.dumps(report))
