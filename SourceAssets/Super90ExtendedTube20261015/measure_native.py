"""Locate the native magazine tube and end cap for exterior mesh authoring."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent
source=O.parent/'Super90Birdcage20261015/Preview/super90.fbx'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(source),use_anim=False)
report=[]
for obj in bpy.context.scene.objects:
    if obj.type!='MESH':continue
    mesh=obj.data;parents=list(range(len(mesh.vertices)))
    def root(i):
        while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
        return i
    for edge in mesh.edges:
        a,b=map(root,edge.vertices)
        if a!=b:parents[b]=a
    # FBX splits hard normals and UV seams into separate vertices. Restore
    # connectivity only for selection; the author's geometry stays untouched.
    coincident={}
    for v in mesh.vertices:
        key=tuple(round(c,6) for c in obj.matrix_world@v.co)
        if key in coincident:
            a,b=root(v.index),root(coincident[key])
            if a!=b:parents[b]=a
        else:coincident[key]=v.index
    groups={}
    for v in mesh.vertices:groups.setdefault(root(v.index),[]).append(v.index)
    faces={}
    for f in mesh.polygons:faces.setdefault(root(f.vertices[0]),[]).append(f.index)
    for key,verts in groups.items():
        points=[obj.matrix_world@mesh.vertices[i].co for i in verts]
        lo=[min(v[k] for v in points) for k in range(3)];hi=[max(v[k] for v in points) for k in range(3)]
        if hi[1]<.25 or lo[2]>-.70 or hi[2]<-.87:continue
        polys=faces.get(key,[])
        names=sorted({mesh.materials[mesh.polygons[i].material_index].name for i in polys})
        report.append({'object':obj.name,'component':key,'vertices':len(verts),'faces':len(polys),
            'min':lo,'max':hi,'materials':names,'face_ids':polys})
(O/'native_components.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for row in sorted(report,key=lambda x:x['max'][1],reverse=True):
    print({k:v for k,v in row.items() if k!='face_ids'},flush=True)
