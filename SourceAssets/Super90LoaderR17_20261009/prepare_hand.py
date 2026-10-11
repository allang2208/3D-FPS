"""Extract the accepted R16 hand and actual handle for hand-only authoring."""
import bpy, json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent; S=O.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'Super90LoaderR16_20261009/Super90_Speedloader_R16.blend'))
rig=bpy.data.objects['SK_Super90']; scene=bpy.context.scene
names=[b.name for b in rig.data.bones]
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
finger=[n for n in names if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))]
rig.animation_data.action=bpy.data.actions['A_Super90_loader_empty_7'];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_set(145);bpy.context.view_layer.update()
pose={b.name:b.matrix.copy() for b in rig.pose.bones}
skin=[]
ob=bpy.data.objects['Super90_V7_M4_BareArmsV6']; xf=rig.matrix_world.inverted()@ob.matrix_world
for v in ob.data.vertices:
    weights={ob.vertex_groups[g.group].name:g.weight for g in v.groups}
    if sum(w for n,w in weights.items() if n in finger or n=='hand_l')>.95:
        skin.append(dict(position=list(xf@v.co),weights=weights))
bolt=bpy.data.objects['Super90_bolt'];xf=rig.matrix_world.inverted()@bolt.matrix_world
verts=[xf@v.co for v in bolt.data.vertices]
outer=[v for v in verts if v.x>max(p.x for p in verts)-.012]
knob=sum(outer,Vector())/len(outer)
def matrices(d):return {n:[list(r) for r in m] for n,m in d.items()}
out=dict(rest=matrices(rest),parents=parents,pose=matrices(pose),finger_names=finger,skin=skin,
    handle_rest_center=list(knob),handle_rest_points=[list(v) for v in outer],frame=145)
scene.frame_set(134);bpy.context.view_layer.update()
out['open_pose']=matrices({b.name:b.matrix.copy() for b in rig.pose.bones})
(O/'hand_inputs.json').write_text(json.dumps(out,separators=(',',':')))
print('HAND_AUTHOR_INPUT',len(skin),'vertices, handle',list(knob),flush=True)
for d in ('index','middle','ring','pinky','thumb'):
    pts=[]
    for k in (1,2,3):
        n=f'{d}_{k:02}_l';vs=[Vector(v['position']) for v in skin if max(v['weights'],key=v['weights'].get)==n]
        pts.append([round(x,4) for x in sum(vs,Vector())/len(vs)])
    print(d,pts,flush=True)
