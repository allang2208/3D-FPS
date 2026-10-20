import bpy,json
from pathlib import Path
from collections import Counter
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'SVCH_Refined.blend'))
report={}
for ob in bpy.data.objects:
    if ob.type!='MESH':continue
    me=ob.data;me.calc_loop_triangles();counts=Counter();small=[]
    for t in me.loop_triangles:
        pts=[me.vertices[i].co for i in t.vertices]
        area=(pts[1]-pts[0]).cross(pts[2]-pts[0]).length*.5
        name=me.materials[t.material_index].name
        counts[name]+=1
        small.append({'area_m2':area,'material':name,'vertices':list(t.vertices),
                      'positions_m':[list(v) for v in pts]})
    report[ob.name]={'triangles':len(me.loop_triangles),'materials':dict(counts),
                    'smallest':sorted(small,key=lambda x:x['area_m2'])[:2]}
(O/'source_topology.json').write_text(json.dumps(report,indent=1))
print('SVCH_TOPOLOGY_READ',json.dumps({k:{'triangles':v['triangles'],'min_area_m2':v['smallest'][0]['area_m2']} for k,v in report.items()}))
