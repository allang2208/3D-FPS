import bpy, json
from pathlib import Path
from collections import Counter
root=Path(__file__).resolve().parent
source=root.parent/'BarkRebuildV21/Staff_NaturalBark_V21.blend'
names=['SM_Staff_head_crystal_'+s for s in ('frozen_crystal','magma_core','jade_spirit_crystal','storm_core')]
with bpy.data.libraries.load(str(source),link=False) as (src,dst):
    dst.objects=names
for o in dst.objects:
    print('AUTHORING_INPUT '+json.dumps({'name':o.name,'verts':len(o.data.vertices),
      'face_sizes':dict(Counter(len(p.vertices) for p in o.data.polygons)),
      'materials':[m.name for m in o.data.materials],
      'material_faces':dict(Counter(p.material_index for p in o.data.polygons)),
      'z_levels':[round(z,3) for z in sorted(set(round(v.co.z,3) for v in o.data.vertices))][:80]}),flush=True)
