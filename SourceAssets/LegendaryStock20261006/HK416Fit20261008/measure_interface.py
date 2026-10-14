import bpy,json,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;P=O.parents[2]
inv=json.loads((P/'SourceAssets/HK416Reworked20260930/source_inventory.json').read_text());objects={v['name']:v for v in inv['objects']}
auth=json.loads((P/'SourceAssets/HK416Reworked20260930/authoring.json').read_text());to_root=Matrix(auth['source_to_weapon_root'])
def bounds(points):return [[float(f(p[i] for p in points)) for i in range(3)] for f in (min,max)]
report={}
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(P/'SourceAssets/HK416Reworked20260930/HK416_Original_Editable.blend'),link=False) as (s,d):d.objects=['Stock_Stick_low','Lower_body_low']
for ob in d.objects:
    pts=[to_root@Matrix(objects[ob.name]['matrix_world'])@v.co for v in ob.data.vertices]
    row={'bounds':bounds(pts)}
    if ob.name=='Stock_Stick_low':
        y=min(p.y for p in pts);rings={}
        for p in pts:
            k=round(p.y,5)
            if k<y+.020:rings.setdefault(k,[]).append(p)
        row['front_rings']={str(k):{'count':len(v),'bounds':bounds(v)} for k,v in sorted(rings.items())}
    report[ob.name]=row
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Integration/Editable/HK416_TacticalStock.blend'))
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    pts=[ob.matrix_world@v.co for v in ob.data.vertices];row={'bounds':bounds(pts)}
    if 'Retained' in ob.name:
        y=min(p.y for p in pts);row['front_3mm_bounds']=bounds([p for p in pts if p.y<y+.003])
    report[ob.name]=row
(O/'interface-measurement.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
