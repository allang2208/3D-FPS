import bpy,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'Working.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
s.frame_set(310);bpy.context.view_layer.update();root=r.pose.bones['WPN_root'].matrix.inverted()
result={'bolt':{},'skin':{}}
deps=bpy.context.evaluated_depsgraph_get()
for ob in s.objects:
    if ob.type=='MESH' and 'Bolt' in ob.name and not ob.hide_render:
        ev=ob.evaluated_get(deps);mesh=ev.to_mesh();M=root@r.matrix_world.inverted()@ev.matrix_world
        vv=[list(M@v.co) for v in mesh.vertices];ff=[list(p.vertices) for p in mesh.polygons]
        result['bolt'][ob.name]={'vertices':vv,'faces':ff};ev.to_mesh_clear()
        print('BOLT',ob.name,[(min(v[i] for v in vv),max(v[i] for v in vv)) for i in range(3)],flush=True)
skin=bpy.data.objects['SK_Manny_Arms_Export']
names=['hand_r']+[b.name for b in r.data.bones if b.name.startswith(('thumb','index','middle','ring','pinky')) and b.name.endswith('_r')]
groups={g.index:g.name for g in skin.vertex_groups};indices=[];verts=[];weights=[]
M=r.matrix_world.inverted()@skin.matrix_world
for v in skin.data.vertices:
    w={groups[g.group]:g.weight for g in v.groups if g.weight>.00001}
    if sum(value for n,value in w.items() if n in names)<.99:continue
    indices.append(v.index);verts.append(list(M@v.co));weights.append(w)
mapping={idx:i for i,idx in enumerate(indices)}
faces=[list(map(mapping.get,p.vertices)) for p in skin.data.polygons if all(i in mapping for i in p.vertices)]
result['skin']={'names':names,'vertices':verts,'weights':weights,'faces':faces,'indices':indices,
    'rest':{b.name:[list(row) for row in b.matrix_local] for b in r.data.bones},
    'parents':{b.name:b.parent.name if b.parent else None for b in r.data.bones}}
(O/'geometry.json').write_text(json.dumps(result),encoding='utf-8')
print('RIGHT_SKIN',len(verts),flush=True)
