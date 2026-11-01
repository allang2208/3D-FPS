import bpy,json,numpy as np
from mathutils import Matrix,Vector
from mathutils.kdtree import KDTree
from pathlib import Path
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24CustomScope20261026/M24_V9_Gameplay_Editable.blend'),use_scripts=False)
r=bpy.data.objects['M24_V9_Rig']
out={'rig':{'scale':list(r.scale),'delta_scale':list(r.delta_scale),'nla':str([(t.name,[(s.name,s.action.name,s.blend_type) for s in t.strips]) for t in r.animation_data.nla_tracks]),'drivers':str([d.data_path for d in r.animation_data.drivers]),'unit':bpy.context.scene.unit_settings.scale_length},'uv':{}}
old={}
for ob in bpy.context.scene.objects:
    if ob.type!='MESH' or ob.name=='M24_V9_BareArms':continue
    ob.data.calc_loop_triangles()
    old[ob.name]={'v':np.array([v.co[:] for v in ob.data.vertices]),'loops':[l.vertex_index for l in ob.data.loops],
      'uv':np.array([v.uv[:] for v in ob.data.uv_layers.active.data])}
bpy.ops.wm.open_mainfile(filepath=str(O/'OriginalGLTF_Reference.blend'),use_scripts=False)
C=Matrix.Rotation(np.pi,4,'Z')
reg=Matrix(json.loads((O.parent/'M24CustomScope20261026/authoring.json').read_text())['static_remix_to_source'])
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    name=next((n for n in old if ob.name.startswith(n[4:]+'_')),None)
    if not name:continue
    # glTF is the selected remix in its author placement, same as its FBX.
    vertices=[C@reg@ob.matrix_world@v.co for v in ob.data.vertices]
    kd=KDTree(len(vertices))
    for i,v in enumerate(vertices):kd.insert(v,i)
    kd.balance();correspond=[kd.find(Vector(v)) for v in old[name]['v']]
    distances=[x[2] for x in correspond]
    uvset={i:[] for i in range(len(ob.data.vertices))}
    for loop,uv in zip(ob.data.loops,ob.data.uv_layers[0].data):uvset[loop.vertex_index].append(np.array(uv.uv[:]))
    errors=[];flipped=[]
    for vi,uv in zip(old[name]['loops'],old[name]['uv']):
        target=uvset[correspond[vi][1]]
        errors.append(min(np.linalg.norm(v-uv) for v in target))
        flipped.append(min(np.linalg.norm(v-np.array((uv[0],1-uv[1]))) for v in target))
    out['uv'][name]={'vertex_distance_max':max(distances),'vertex_distance_mean':float(np.mean(distances)),
        'uv_same_mean':float(np.mean(errors)),'uv_flip_v_mean':float(np.mean(flipped))}
(O/'source_comparison.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out),flush=True)
