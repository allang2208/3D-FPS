"""Read the generated hand surface to place its local custom skeleton. No render."""
import bpy
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT/'Meshy/candidate01/downloads'
OUT = ROOT/'LocalRig'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(SOURCE/'model.fbx'), use_custom_normals=True)
objects = []
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH':
        continue
    v = np.array([list(obj.matrix_world@point.co) for point in obj.data.vertices])
    edges = np.array([list(e.vertices) for e in obj.data.edges], dtype=np.int32)
    lo, hi = v.min(axis=0), v.max(axis=0)
    h = hi[2]-lo[2]
    vn = (v-np.array([(lo[0]+hi[0])/2,(lo[1]+hi[1])/2,lo[2]]))/h
    sections = []
    for cut in (.25,.35,.45,.50,.55,.60,.65,.70,.75,.80,.85,.90):
        parent = np.arange(len(v),dtype=np.int32)
        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        mask = vn[:,2] > cut
        for a,b in edges[mask[edges[:,0]]&mask[edges[:,1]]]:
            a,b = find(a),find(b)
            if a!=b:
                parent[b]=a
        groups={}
        for i in np.flatnonzero(mask):
            groups.setdefault(int(find(i)),[]).append(int(i))
        components=[]
        for ids in groups.values():
            if len(ids)<15:
                continue
            points=vn[ids]
            components.append({'vertices':len(ids),'min':points.min(axis=0).tolist(),
                               'max':points.max(axis=0).tolist(),'center':points.mean(axis=0).tolist()})
        sections.append({'cut':cut,'components':sorted(components,key=lambda c:c['center'][0])})
    name=obj.name.replace('/','_')
    np.savez_compressed(OUT/(name+'_surface.npz'),vertices=v,normalized=vn,edges=edges)
    objects.append({'object':obj.name,'world_min':lo.tolist(),'world_max':hi.tolist(),
                    'vertices':len(v),'polygons':len(obj.data.polygons),
                    'quad_faces':sum(len(p.vertices)==4 for p in obj.data.polygons),
                    'materials':[m.name for m in obj.data.materials if m],
                    'normalized_slices':sections})
report={'source':str(SOURCE/'model.fbx'),'purpose':'surface coordinates for custom hand bone placement',
        'objects':objects,'rendered':False,'animation_tested':False}
(OUT/'input_geometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('RIG_GEOMETRY '+json.dumps(report))
