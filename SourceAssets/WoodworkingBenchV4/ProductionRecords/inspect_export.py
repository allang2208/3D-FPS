import bpy,json,collections,math
from pathlib import Path
W=Path('C:/Users/allan/Documents/Codex/2026-10-04/task-2/woodworking_v4_import_20261008')
report={}
for name in ['SM_WoodworkingBench','SM_WoodworkingBenchBody','SM_WoodworkingSawBlade']:
    o=bpy.data.objects[name];m=o.data;m.calc_loop_triangles();uv=m.uv_layers.active.data;counts=collections.Counter();by=collections.Counter()
    for t in m.loop_triangles:
        a,b,c=[m.vertices[i].co for i in t.vertices];area=(b-a).cross(c-a).length*.5
        aa,bb,cc=[uv[i].uv for i in t.loops];u=(bb-aa).cross(cc-aa)
        if area<1e-12:counts['zero_area']+=1
        elif abs(u)<1e-12:counts['nonzero_area_zero_uv']+=1;by[m.materials[t.material_index].name]+=1
    report[name]={'triangles':len(m.loop_triangles),'counts':dict(counts),'zero_uv_materials':dict(by)}
(W/'geometry_audit.json').write_text(json.dumps(report,indent=2));print('GEOMETRY_AUDIT',json.dumps(report))
