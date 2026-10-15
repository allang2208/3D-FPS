"""Read the original pommel geometry for dimensional authoring."""
import bpy, json
from pathlib import Path
P = Path(__file__).resolve().parent
ROOT = P.parents[2]
source = ROOT / 'SourceAssets/SteelWarhammer20261014/ModulesV1/Warhammer_Modular_Editable.blend'
with bpy.data.libraries.load(str(source), link=False) as (a, b):
    b.objects = ['SM_Warhammer_pommel_factory']
obj = b.objects[0]
mesh = obj.data
mesh.calc_loop_triangles()
points = [v.co for v in mesh.vertices]
lo = [min(v[i] for v in points) for i in range(3)]
hi = [max(v[i] for v in points) for i in range(3)]
sections = []
for i in range(15):
    z = lo[2] + (hi[2] - lo[2]) * (i + .01) / 14.02
    xy = []
    for t in mesh.loop_triangles:
        vs = [mesh.vertices[n].co for n in t.vertices]
        for a, b in zip(vs, vs[1:] + vs[:1]):
            if (a.z <= z < b.z) or (b.z <= z < a.z):
                c = a.lerp(b, (z-a.z)/(b.z-a.z))
                xy.append([c.x, c.y])
    if xy:
        sections.append({'z': z, 'min': [min(p[j] for p in xy) for j in range(2)],
                         'max': [max(p[j] for p in xy) for j in range(2)]})
record = {'source': str(source), 'object': obj.name, 'pivot_m': list(obj.location),
          'bounds_local_m': [lo, hi], 'materials': [m.name for m in mesh.materials],
          'triangles': len(mesh.loop_triangles), 'sections': sections}
(P/'factory_geometry.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print('FACTORY_POMMEL ' + json.dumps(record), flush=True)
