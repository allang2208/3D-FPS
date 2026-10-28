import bpy,json
from pathlib import Path
from collections import defaultdict
P=Path(__file__).resolve().parent
sources=json.loads((P.parent/'blade-layout-source.json').read_text('utf-8'))
bpy.ops.wm.read_factory_settings(use_empty=True)
report=[]
for source in sources:
    with bpy.data.libraries.load(source['blend'],link=False) as (a,b):b.objects=[source['object']]
    obj=b.objects[0];bpy.context.collection.objects.link(obj);mesh=obj.data
    uv=mesh.uv_layers.active
    groups=defaultdict(list)
    for poly in mesh.polygons:
        for loop in poly.loop_indices:
            p=mesh.vertices[mesh.loops[loop].vertex_index].co
            t=uv.data[loop].uv
            groups[(round(t.x,5),round(t.y,5))].append(tuple(p))
    spans=[]
    for key,points in groups.items():
        if len(points)<2:continue
        spread=[max(v[i] for v in points)-min(v[i] for v in points) for i in range(3)]
        if spread[0]>.001 or spread[2]>.001:spans.append({'uv':key,'spread':spread,'positions':points[:5]})
    entry={'kind':source['kind'],'matrix_world':[list(r) for r in obj.matrix_world],
        'uv_layers':[x.name for x in mesh.uv_layers],'active_uv':uv.name,'vertices':len(mesh.vertices),'polygons':len(mesh.polygons),
        'conflicting_uv_coordinates':len(spans),'largest_conflicts':sorted(spans,key=lambda v:max(v['spread'][0],v['spread'][2]),reverse=True)[:4]}
    report.append(entry)
    print('PROJECTION '+json.dumps(entry),flush=True)
(P/'projection-diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
