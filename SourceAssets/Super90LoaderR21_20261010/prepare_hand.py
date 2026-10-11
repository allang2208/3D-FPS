"""Read R20 production author poses and the native V7 skin for grasp authoring."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'Super90LoaderR20_20261010/Super90_Speedloader_R20.blend'))
rig=bpy.data.objects['SK_Super90'];scene=bpy.context.scene
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};names=list(rest)
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
def packed(p):return {n:[list(row) for row in m] for n,m in p.items()}
poses={}
for branch,end in (('normal',144),('empty',180),('cycle',66)):
    name='A_Super90_loader_'+(branch if branch=='cycle' else branch+'_7')
    rig.animation_data.action=bpy.data.actions[name];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
    poses[branch]=[]
    for f in range(end+1):
        scene.frame_set(f);bpy.context.view_layer.update();poses[branch].append({b.name:b.matrix.copy() for b in rig.pose.bones})
(O/'source_poses.json').write_text(json.dumps({b:[packed(p) for p in rows] for b,rows in poses.items()},separators=(',',':')),encoding='utf-8')
finger=[n for n in names if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))]
skin=[];ob=bpy.data.objects['Super90_V7_M4_BareArmsV6'];xf=rig.matrix_world.inverted()@ob.matrix_world
for v in ob.data.vertices:
    w={ob.vertex_groups[g.group].name:g.weight for g in v.groups}
    if sum(a for n,a in w.items() if n in finger or n=='hand_l')>.95:skin.append(dict(position=list(xf@v.co),weights=w))
ob=bpy.data.objects['Super90_bolt'];xf=rig.matrix_world.inverted()@ob.matrix_world;verts=[xf@v.co for v in ob.data.vertices]
outer=[v for v in verts if v.x>max(p.x for p in verts)-.012]
knob=sum(outer,Vector())/len(outer)
out=dict(rest=packed(rest),parents=parents,pose=packed(poses['empty'][150]),open_pose=packed(poses['empty'][134]),
    push_pose=packed(poses['empty'][100]),finger_names=finger,skin=skin,handle_rest_center=list(knob),handle_rest_points=[list(v) for v in outer])
(O/'hand_inputs.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
print('R21_AUTHOR_INPUT',len(skin),'skin vertices','root bones',[n for n in names if not parents[n]],flush=True)
print('R21_HANDLE',list(knob),'left wrist',list(poses['empty'][150]['hand_l'].translation),flush=True)
