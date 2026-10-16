"""Read the existing binding's contact geometry for local bookmark authoring."""
import bpy,json
from mathutils.bvhtree import BVHTree
from pathlib import Path
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'AlchemyManualFinePress20261016/AlchemyManualFinePress.blend'),load_ui=False,use_scripts=False)
body=bpy.data.objects['SM_AlchemyManualOpen']
records={}
for mat in ('M_BookCover','M_BookPages','RecipeLeft','RecipeRight'):
    ids={i for f in body.data.polygons if body.data.materials[f.material_index].name==mat for i in f.vertices}
    pts=[body.matrix_world@body.data.vertices[i].co for i in ids]
    records[mat]=dict(min=[min(v[a] for v in pts) for a in range(3)],max=[max(v[a] for v in pts) for a in range(3)])
    near=[v for v in pts if abs(v.x-13.2)<1.3 and v.y>11.4]
    records[mat]['near_upper_right']=[list(v) for v in sorted(near,key=lambda p:-p.z)[:10]]
(ROOT/'host-geometry.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('BOOK_CONTACTS '+json.dumps(records))
tree=BVHTree.FromPolygons([body.matrix_world@v.co for v in body.data.vertices],[list(f.vertices) for f in body.data.polygons if body.data.materials[f.material_index].name=='M_BookCover'])
for x in (12.3,13.2,14.1):
    for y in (11.65,11.85,12.02):
        hit=tree.ray_cast((x,y,10),(0,0,-1))[0]
        print('COVER_ANCHOR',x,y,list(hit) if hit else None)
