"""Read authoring islands in the current SVD weapon frame for material partitioning."""
import bpy, json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
S=O.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'SVDCompletion20260923/SVD_Complete_Editable.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
ob=bpy.data.objects['SM_SVD_Body']
transform=rig.data.bones['WPN_root'].matrix_local.inverted()@rig.matrix_world.inverted()@ob.matrix_world
parent=list(range(len(ob.data.vertices)))
def find(i):
    while parent[i]!=i:
        parent[i]=parent[parent[i]];i=parent[i]
    return i
for e in ob.data.edges:
    a,b=map(find,e.vertices)
    if a!=b:parent[b]=a
groups={}
for face in ob.data.polygons:
    entry=groups.setdefault(find(face.vertices[0]),{'faces':[],'vertices':set()})
    entry['faces'].append(face.index);entry['vertices'].update(face.vertices)
rows=[]
for key,entry in groups.items():
    points=[transform@ob.data.vertices[i].co for i in entry['vertices']]
    lo=Vector([min(p[a] for p in points) for a in range(3)])
    hi=Vector([max(p[a] for p in points) for a in range(3)])
    rows.append(dict(island=key,faces=entry['faces'],min=list(lo),max=list(hi),size=list(hi-lo),center=list((lo+hi)*.5)))
rows.sort(key=lambda r:len(r['faces']),reverse=True)
(O/'body_regions.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('SVD_BODY_REGIONS '+json.dumps([{k:(len(v) if k=='faces' else v) for k,v in r.items()} for r in rows[:20]]),flush=True)
