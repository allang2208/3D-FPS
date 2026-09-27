"""Read the source and authored mesh winding without modifying either file."""
import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'DarkBow20260925/WoodLongbow20260925'
report={}
def describe(obj):
    obj.data.calc_loop_triangles()
    vertices=[obj.matrix_world@v.co for v in obj.data.vertices]
    volume=sum(vertices[t.vertices[0]].dot(vertices[t.vertices[1]].cross(vertices[t.vertices[2]]))/6
        for t in obj.data.loop_triangles)
    return {'object':obj.name,'triangles':len(obj.data.loop_triangles),'signed_volume':volume,
        'custom_normals':obj.data.has_custom_normals}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(P/'source.glb'))
report['source']=[describe(o) for o in bpy.data.objects if o.type=='MESH' and not o.name.startswith('sweep4')]
bpy.ops.wm.open_mainfile(filepath=str(P/'WoodLongbow_Editable.blend'))
report['authored']=[describe(o) for o in bpy.data.objects if o.type=='MESH']
out=P.parents[2]/'Saved/BowModelRepair20260926/orientation.json'
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BOW_MESH_ORIENTATION',json.dumps(report),flush=True)
