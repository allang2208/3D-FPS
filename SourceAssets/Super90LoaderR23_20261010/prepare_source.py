"""Read the saved R21 poses and real skin for the reported wrist/bolt defects."""
import bpy, json
from pathlib import Path
O=Path(__file__).parent; S=O.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'Super90LoaderR21_20261010/Super90_Speedloader_R21.blend'))
rig=bpy.data.objects['SK_Super90']; scene=bpy.context.scene
def packed(p):return {n:[list(row) for row in m] for n,m in p.items()}
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
poses={}
for branch,end in (('normal',144),('empty',180),('cycle',66)):
    name='A_Super90_loader_'+(branch if branch=='cycle' else branch+'_7')
    rig.animation_data.action=bpy.data.actions[name];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
    poses[branch]=[]
    for f in range(end+1):
        scene.frame_set(f);bpy.context.view_layer.update()
        poses[branch].append(packed({b.name:b.matrix.copy() for b in rig.pose.bones}))
(O/'source_poses.json').write_text(json.dumps(poses,separators=(',',':')))
geometry={}
for ob in scene.objects:
    if ob.type!='MESH' or not (ob.name.startswith('Super90_') or 'Loader' in ob.name):continue
    xf=rig.matrix_world.inverted()@ob.matrix_world
    geometry[ob.name]=dict(positions=[list(xf@v.co) for v in ob.data.vertices],
        weights=[{ob.vertex_groups[g.group].name:g.weight for g in v.groups} for v in ob.data.vertices],
        faces=[list(p.vertices) for p in ob.data.polygons])
(O/'geometry.json').write_text(json.dumps(dict(rest=packed(rest),parents=parents,meshes=geometry),separators=(',',':')))
print('R23_SOURCE',json.dumps({n:len(m['positions']) for n,m in geometry.items()}),flush=True)
for n in rest:
    if n.endswith('_l') and not n.startswith(('index','middle','ring','pinky','thumb')):
        print('BONE',n,parents[n],list(rest[n].translation),flush=True)
