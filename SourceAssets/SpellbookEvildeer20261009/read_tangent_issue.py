"""Locate the faces behind the importer's reported tangent warning."""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Spellbook_Alchemy.blend'))
for name in ('SM_Spellbook_Alchemy_Open','SK_Spellbook_Alchemy'):
    obj=bpy.data.objects[name];mesh=obj.data;mesh.calc_loop_triangles();uv=mesh.uv_layers.active.data
    bad=[]
    for t in mesh.loop_triangles:
        a,b,c=[uv[i].uv.copy() for i in t.loops]
        area=abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))
        if area<1e-10 or t.area<1e-7:
            bad.append({'face':t.polygon_index,'mat':mesh.polygons[t.polygon_index].material_index,'uv_area':area,'area':t.area,'xyz':[list(mesh.vertices[i].co) for i in t.vertices],'uv':[list(v) for v in (a,b,c)]})
    print(name,json.dumps({'count':len(bad),'examples':bad[:10]}))
