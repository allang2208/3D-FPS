import json,sys
from pathlib import Path
O=Path(__file__).parent;old=O.parent/'Super90ContactR8_20261008/render_saved.py'
ns={'__file__':str(old)};exec(compile(old.read_text().split('items=[]')[0],str(old),'exec'),ns)
print('PYTHON',sys.version,flush=True)
out=[]
for key in ('weapon','props','guide'):
 for ob in ns['groups'][key]:
    ob.data.calc_loop_triangles()
    for i,mat in enumerate(ob.data.materials):
        ts=[t for t in ob.data.loop_triangles if t.material_index==i];weights={}
        for t in ts:
         for vi in t.vertices:
          for g in ob.data.vertices[vi].groups:
            n=ob.vertex_groups[g.group].name;weights[n]=weights.get(n,0)+g.weight
        row={'group':key,'object':ob.name,'material':mat.name if mat else None,'triangles':len(ts),'bones':sorted(weights.items(),key=lambda x:-x[1])[:10]};out.append(row);print('MATERIAL',row,flush=True)
(O/'Diagnostics/material_groups.json').write_text(json.dumps(out,indent=2))
