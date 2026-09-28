import bpy,json
from pathlib import Path
from mathutils import Matrix
root=Path(__file__).parent/'FloorTrim'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(root/'SM_GodSpaceStructure_Before.fbx'),use_custom_normals=True)
report=[]
for obj in [o for o in bpy.context.scene.objects if o.type=='MESH']:
    obj.data.transform(obj.matrix_world);obj.matrix_world=Matrix.Identity(4)
    me=obj.data;parent=list(range(len(me.vertices)))
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for edge in me.edges:
        a,b=map(find,edge.vertices);parent[b]=a
    groups={}
    for v in me.vertices:groups.setdefault(find(v.index),[]).append(v.index)
    for ids in groups.values():
        key=find(ids[0]);faces=[p for p in me.polygons if find(p.vertices[0])==key]
        lo=[min(me.vertices[i].co[k] for i in ids) for k in range(3)]
        hi=[max(me.vertices[i].co[k] for i in ids) for k in range(3)]
        if hi[2]<0 or lo[2]>1.3:continue
        report.append({'object':obj.name,'vertices':len(ids),'faces':len(faces),'min':lo,'max':hi,
            'materials':sorted({me.materials[p.material_index].name for p in faces})})
(root/'geometry-before.json').write_text(json.dumps(report,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(root/'Structure_Before.blend'))
print('FLOOR_PARTS '+json.dumps(report))
