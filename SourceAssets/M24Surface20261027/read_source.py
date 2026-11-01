import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24ActionLayout20261027/M24_ActionLayout_Editable.blend'),use_scripts=False)
out={}
for ob in bpy.context.scene.objects:
    if ob.type!='MESH' or 'Arms' in ob.name:continue
    pts=[ob.matrix_world@v.co for v in ob.data.vertices]
    out[ob.name]={'vertices':len(pts),'triangles':sum(len(p.vertices)-2 for p in ob.data.polygons),'bounds':[[min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]], 'materials':[m.name for m in ob.data.materials], 'uvs':[uv.name for uv in ob.data.uv_layers], 'groups':[g.name for g in ob.vertex_groups], 'matrix':[list(x) for x in ob.matrix_world]}
(O/'source_geometry.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('M24_SOURCE_RECORDED')
