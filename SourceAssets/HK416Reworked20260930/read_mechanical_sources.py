import bpy,json
from pathlib import Path
O=Path(__file__).parent;S=O.parent;out={}
bpy.ops.wm.open_mainfile(filepath=str(S/'M4TacticalToss20260910/M4_Hand_MAT_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];root=r.data.bones['WPN_root'].matrix_local.copy();inv=root.inverted()
out['donor']={'root':[list(row) for row in root],'actions':[a.name for a in bpy.data.actions],
 'mechanical_bones':{b.name:{'head':list(inv@b.head_local),'matrix':[list(row) for row in b.matrix_local]} for b in r.data.bones if b.name.startswith('WPN_')},'meshes':[]}
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    points=[inv@ob.matrix_world@v.co for v in ob.data.vertices]
    out['donor']['meshes'].append({'name':ob.name,'materials':[m.name for m in ob.data.materials],
        'lo':[min(p[i] for p in points) for i in range(3)],'hi':[max(p[i] for p in points) for i in range(3)]})
bpy.ops.wm.open_mainfile(filepath=str(O/'HK416_Original_Editable.blend'))
for name in ('Triger_low','ironsight_low','Muzzle_low','Buttons_low','push_button_low'):
    ob=bpy.data.objects[name];mesh=ob.data;parents=list(range(len(mesh.vertices)))
    def find(i):
        while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
        return i
    for edge in mesh.edges:parents[find(edge.vertices[0])]=find(edge.vertices[1])
    components={}
    for v in mesh.vertices:components.setdefault(find(v.index),[]).append(v.index)
    records=[]
    for ids in components.values():
        points=[ob.matrix_world@mesh.vertices[i].co for i in ids]
        records.append({'first':ids[0],'count':len(ids),'lo':[min(p[i] for p in points) for i in range(3)],'hi':[max(p[i] for p in points) for i in range(3)]})
    out[name]=records
(O/'mechanical_sources.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out),flush=True)
