"""Read native contact geometry for authoring; no rendering or runtime tests."""
import bpy, json
from pathlib import Path
O=Path(__file__).parent
S=O.parent/'BenelliM4Super9020261006'
bpy.ops.wm.open_mainfile(filepath=str(S/'Super90_Gameplay_Editable.blend'))
rig=bpy.data.objects['SK_Super90']; scene=bpy.context.scene
out={'rig_matrix':list(map(list,rig.matrix_world)), 'rest':{},'poses':{},'meshes':[]}
out['rest']={b.name:list(map(list,b.matrix_local)) for b in rig.data.bones}
out['parents']={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
for kind,frame in [('idle',0),('reload_full',0),('reload_full',44),('reload_full',360),('reload_full',375),('reload_full',395)]:
    a=bpy.data.actions['A_Super90_'+kind];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
    scene.frame_set(frame);bpy.context.view_layer.update()
    out['poses'][f'{kind}_{frame}']={b.name:list(map(list,b.matrix)) for b in rig.pose.bones}
for ob in scene.objects:
    if ob.type!='MESH':continue
    out['meshes'].append({'name':ob.name,'materials':[m.name if m else '' for m in ob.data.materials], 'vertices':len(ob.data.vertices)})
(O/'author_inputs.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
names=['WPN_root','WPN_bolt','12gauge','hand_l','hand_r','upperarm_l','lowerarm_l','WPN_SOCKET_Magazine','WPN_FrontSight','WPN_RearSight']
for key in out['poses']:
    print(key,{n:[round(out['poses'][key][n][i][3],4) for i in range(3)] for n in names if n in out['poses'][key]})
print('MESHES',out['meshes'])
print('BONES',list(out['rest']))
