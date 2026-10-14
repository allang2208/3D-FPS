import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;inv=json.loads((O.parents[2]/'SourceAssets/HK416Reworked20260930/source_inventory.json').read_text())
boxes={e['name']:e['bounds'] for e in inv['objects'] if e.get('parent')=='Laser_sight' and e.get('bounds')}
def load(side,dy):
    bpy.ops.wm.open_mainfile(filepath=str(O/'Editable'/f'HK416-laser-{side}.blend'));ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');v=[p.co+Vector((0,dy,0)) for p in ob.data.vertices];f=[list(p.vertices) for p in ob.data.polygons];return v,f,BVHTree.FromPolygons(v,f)
out={}
for dy in (0.,-.012):
    a,fa,ta=load(1,0);b,fb,tb=load(2,dy);hits=ta.overlap(tb);count={};points=[]
    for ai,bi in hits:
        p=sum((a[i] for i in fa[ai]),Vector())/len(fa[ai]);points.append(p)
        parts=[name for name,box in boxes.items() if all(box['min'][i]*4-.0001<=p[i]<=box['max'][i]*4+.0001 for i in range(3))]
        label='|'.join(parts);count[label]=count.get(label,0)+1
    out[str(dy)]={'parts':count,'crossing_bounds':[[fun(p[i] for p in points) for i in range(3)] for fun in (min,max)]}
(O/'crossing-diagnosis.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
