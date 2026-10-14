import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;report={}
for key in ('HK416-laser','HK416-flashlight'):
    g=json.loads((O/'Cache'/(key+'.json')).read_text());t=BVHTree.FromPolygons(g['vertices'],g['faces'])
    h=json.loads((O/'Cache'/(key+'-1-host.json')).read_text());host=BVHTree.FromPolygons(h['vertices'],h['faces']);rows=[]
    for x in (-.16,-.14,-.12,-.10,-.08,-.06,-.04,-.02):
        cells=[]
        for y in (-.01,0,.01):
            v=t.ray_cast(Vector((x,y,.15)),Vector((0,0,-1)),.2)[0];p=host.ray_cast(Vector((x,y,-.03)),Vector((0,0,1)),.2)[0]
            cells.append([round(v.z*1000,2) if v else None,round(p.z*1000,2) if p else None])
        rows.append([x*1000,cells])
    report[key]=rows
(O/'hk-contact-plan.json').write_text(json.dumps(report,indent=2))
print('HK_PLAN',report)
