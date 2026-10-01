"""Read the exported source's real bind geometry and skin influence profiles."""
import bpy, json
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(ROOT/'source_fbx/Rampage.fbx'), use_anim=False)
rig = next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
mesh = max((o for o in bpy.context.scene.objects if o.type=='MESH'), key=lambda o:len(o.data.vertices))
v = np.empty(len(mesh.data.vertices)*3, np.float32)
mesh.data.vertices.foreach_get('co', v)
v = v.reshape(-1,3)
m = np.array(mesh.matrix_world)
v = v@m[:3,:3].T+m[:3,3]
group_names = [g.name for g in mesh.vertex_groups]
w = np.zeros((len(v),len(group_names)),np.float32)
for vertex in mesh.data.vertices:
    for g in vertex.groups: w[vertex.index,g.group] = g.weight
np.savez_compressed(ROOT/'donor_skin.npz', vertices=v, weights=w, bone_names=np.array(group_names))
bind = {}
for bone in rig.data.bones:
    bind[bone.name] = {'head':list(rig.matrix_world@bone.head_local),
        'tail':list(rig.matrix_world@bone.tail_local),
        'matrix':list(map(list,rig.matrix_world@bone.matrix_local)),
        'parent':bone.parent.name if bone.parent else None}
(ROOT/'donor_bind.json').write_text(json.dumps(bind,indent=2))
print('RAMPAGE_BIND_SKIN_EXTRACTED '+json.dumps({'vertices':len(v),'polygons':len(mesh.data.polygons),
    'arm':{n:bind[n]['head'] for n in ['clavicle_r','upperarm_r','lowerarm_r','hand_r']}}),flush=True)
