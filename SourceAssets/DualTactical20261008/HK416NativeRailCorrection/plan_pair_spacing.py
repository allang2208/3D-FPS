import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;geo={};trees={}
for kind in ('laser','flashlight','blessed_laser'):
    for side in (1,2):
        bpy.ops.wm.open_mainfile(filepath=str(O/'Editable'/f'HK416-{kind}-{side}.blend'))
        ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');v=[p.co.copy() for p in ob.data.vertices];f=[list(p.vertices) for p in ob.data.polygons];geo[kind,side]=(v,f);trees[kind,side]=BVHTree.FromPolygons(v,f)
report={}
for kind in ('laser','flashlight','blessed_laser'):
    v,f=geo[kind,2];candidates=[]
    # Native clamp spans Y .201..235; keep it on the existing .056..298 rail.
    offsets=sorted(range(-128,57,4),key=abs)
    for mm in offsets:
        t=BVHTree.FromPolygons([p+Vector((0,mm/1000,0)) for p in v],f)
        hits={a:len(t.overlap(trees[a,1])) for a in ('laser','flashlight','blessed_laser')}
        candidates.append({'offset_mm':mm,'crossings':hits})
        if not any(hits.values()):break
    report[kind]=candidates
    print('SPACING',kind,candidates[-1],flush=True)
(O/'spacing-plan.json').write_text(json.dumps(report,indent=2))
