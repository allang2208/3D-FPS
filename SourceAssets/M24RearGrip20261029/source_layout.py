"""Read authoring geometry to locate the M24 stock-neck surface; no asset edits."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend'),use_scripts=False)
ob=bpy.data.objects['M24_base'];mesh=ob.data
parent=list(range(len(mesh.vertices)))
def root(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return i
def join(a,b):parent[root(a)]=root(b)
lookup={}
for v in mesh.vertices:
    key=tuple(round(x,6) for x in v.co)
    if key in lookup:join(v.index,lookup[key])
    else:lookup[key]=v.index
for e in mesh.edges:join(*e.vertices)
groups={}
for v in mesh.vertices:groups.setdefault(root(v.index),[]).append(v.index)
rows=[]
for indices in groups.values():
    pts=[mesh.vertices[i].co for i in indices]
    rows.append(dict(vertices=len(indices),first=min(indices),lo=[min(p[k] for p in pts) for k in range(3)],hi=[max(p[k] for p in pts) for k in range(3)]))
rows.sort(key=lambda r:r['vertices'],reverse=True)
rig=bpy.data.objects['M24_V9_Rig']
pose=json.loads((O.parent/'M24GripFinish20261028/grip_pose.json').read_text())
wpn=Matrix(pose['WPN_root']);bind=rig.data.bones['WPN_root'].matrix_local
hands={n:list(bind@wpn.inverted()@Matrix(pose[n]).translation) for n in ('hand_r','thumb_03_r','index_03_r','middle_03_r','ring_03_r','pinky_03_r')}
report=dict(source=bpy.data.filepath,components=rows,hand_contact_source=hands,materials=[m.name for m in mesh.materials],weights=[g.name for g in ob.vertex_groups])
(O/'source_layout.json').write_text(json.dumps(report,indent=2))
print('M24_STOCK_SOURCE',json.dumps(report),flush=True)
