import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
report={}
for key in ['phantom_reargrip','balanced_reargrip','stable_antislip_reargrip']:
    bpy.ops.wm.open_mainfile(filepath=str(O/f'SM_PKM_{key}.blend'),use_scripts=False)
    ob=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.name!='PKM_GripTang')
    mesh=ob.data
    bv=BVHTree.FromPolygons([v.co for v in mesh.vertices],[list(p.vertices) for p in mesh.polygons])
    samples=[]
    for x in [-.010,0,.010]:
        for y in [-.010,-.005,0,.005,.010,.015,.020,.025,.030,.035]:
            hit=bv.ray_cast(Vector((x,y,.06)),Vector((0,0,-1)),.12)[0]
            samples.append([x,y,hit.z if hit else None])
    cuts={}
    for z in [.004,.0015,0,-.002]:
        points=[]
        for edge in mesh.edges:
            a,b=[mesh.vertices[i].co for i in edge.vertices]
            if (a.z-z)*(b.z-z)<0:
                points.append(a+(b-a)*((z-a.z)/(b.z-a.z)))
        cuts[z]={'min':[min(p[i] for p in points) for i in range(2)],'max':[max(p[i] for p in points) for i in range(2)]}
    report[key]={'top_surface':samples,'cuts':cuts}
(O/'neck_measurements.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
