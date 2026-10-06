import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parents[3];R=P/'SourceAssets/BlessedLaser20261006/Model/MountRepair'
auth=json.loads((R/'Inputs/authoring-v1.json').read_text());report={}
for family,e in auth.items():
    f=Vector(e['forward_blender']);origin=Vector(e['emitter_blender_m']);s=e['scale']
    desired=Vector((0,0,1)) if family in ('M1911','G18','PitViper2011','DanWesson715') else Vector((0,1,0)) if family in ('RSH12','ASH12') else Vector((-1,0,0))
    up=(desired-f*desired.dot(f)).normalized();frame=Matrix((f,up.cross(f),up));geo=json.loads((R/'Hosts'/(family+'-geometry.json')).read_text())
    verts=[frame@(Vector(v)-origin) for v in geo['vertices']];tree=BVHTree.FromPolygons(verts,geo['faces']);rows=[]
    xs=[x/1000*s for x in (-65,-55,-45,-35,-25,-15)];ys=[y/1000*s for y in (-15,-10,-5,0,5,10,15)]
    for x in xs:
        heights=[]
        for y in ys:
            hit=tree.ray_cast(Vector((x,y,.018*s)),Vector((0,0,1)),.15)[0]
            heights.append(round(hit.z*1000,2) if hit else None)
        rows.append(heights)
    report[family]=dict(up=list(up),x=xs,y=ys,z_mm=rows)
(R/'surface_plan.json').write_text(json.dumps(report,indent=2))
for k,v in report.items():print(k,v['z_mm'])
