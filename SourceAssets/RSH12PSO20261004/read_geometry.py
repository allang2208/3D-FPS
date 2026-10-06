import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'PSO1Russian20260923/PSO1_PKM_Editable.blend'))
r={}
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    points=[ob.matrix_world@v.co for v in ob.data.vertices]
    r[ob.name]=dict(matrix=[list(row) for row in ob.matrix_world],visible=not ob.hide_render,
        bounds=[[min(p[k] for p in points) for k in range(3)],[max(p[k] for p in points) for k in range(3)]],
        slots=[m.name if m else '' for m in ob.data.materials],vertices=len(points),colors=[l.name for l in ob.data.color_attributes])
(O/'geometry.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))

body=bpy.data.objects['PSO_ScopeBody']
for x0,x1 in [(-.2,-.12),(-.12,-.098),(-.098,-.06),(-.06,-.02),(-.02,.02),(.02,.05),(.05,.13)]:
 vs=[v.co for v in body.data.vertices if x0<=v.co.x<x1]
 print('BODY_SEGMENT',x0,x1,[[min(p[k] for p in vs) for k in range(3)],[max(p[k] for p in vs) for k in range(3)]] if vs else [])
