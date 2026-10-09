"""Read source shading and UV data for the reported receiver facets."""
import bpy, json
from pathlib import Path
from collections import Counter
O=Path(__file__).parent;S=O.parent/'BenelliM4Super9020261006'
result={}
for label,file in [('original','BenelliM4_Original_Editable.blend'),('native','Super90_Gameplay_Editable.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(S/file))
    result[label]=[]
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH' or ('benelli' not in obj.name.lower() and not obj.name.startswith('Super90_')):continue
        mesh=obj.data
        result[label].append({'object':obj.name,'vertices':len(mesh.vertices),'faces':len(mesh.polygons),
            'custom_normals':mesh.has_custom_normals,'smooth_faces':sum(p.use_smooth for p in mesh.polygons),
            'uv_layers':[uv.name for uv in mesh.uv_layers],
            'uv_bounds':[[min(v.uv[i] for v in uv.data),max(v.uv[i] for v in uv.data)] for uv in mesh.uv_layers for i in range(2)],
            'slots':[m.name if m else None for m in mesh.materials],
            'material_faces':dict(Counter(p.material_index for p in mesh.polygons)),
            'normal_face_deviation_max':max(((mesh.corner_normals[loop].vector-p.normal).length for p in mesh.polygons for loop in p.loop_indices),default=0)})
(O/'mesh_inputs.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
