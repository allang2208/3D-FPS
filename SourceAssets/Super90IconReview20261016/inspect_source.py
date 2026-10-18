import bpy,json,collections
from pathlib import Path
from mathutils import Matrix
R=Path('D:/FPS3D/FPSGAME');O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(R/'SourceAssets/Super90CommonStocks20261013/Inputs/super90.fbx'),use_anim=False)
ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');ob.data.transform(ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear()
for other in list(bpy.context.scene.objects):
    if other!=ob:bpy.data.objects.remove(other,do_unlink=True)
me=ob.data;parent=list(range(len(me.vertices)))
def root(a):
    while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
    return a
def join(a,b):parent[root(a)]=root(b)
points={}
for v in me.vertices:
    k=tuple(round(c,6) for c in v.co)
    if k in points:join(v.index,points[k])
    else:points[k]=v.index
for e in me.edges:join(*e.vertices)
groups=collections.defaultdict(list)
for p in me.polygons:groups[root(p.vertices[0])].append(p)
report=[]
for faces in groups.values():
    ids=sorted({v for p in faces for v in p.vertices});vs=[me.vertices[v].co for v in ids]
    report.append(dict(index=len(report),faces=len(faces),materials=sorted({p.material_index for p in faces}),lo=[round(min(v[k] for v in vs),5) for k in range(3)],hi=[round(max(v[k] for v in vs),5) for k in range(3)],face_ids=[p.index for p in faces]))
(O/'source_islands.json').write_text(json.dumps(dict(materials=[m.name for m in me.materials],islands=report),indent=2))
print(json.dumps(dict(materials=[m.name for m in me.materials],islands=[{k:v for k,v in r.items() if k!='face_ids'} for r in report if not set(r['materials']).intersection({0,1,2,3,12})]),indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'NativeSource.blend'))
