import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;S=O.parents[1]
bpy.ops.wm.open_mainfile(filepath=str(S/'G18Integration20260929/Single/G18_single_Editable.blend'))
r=bpy.data.objects['SK_G18_Manny'];scene=bpy.context.scene
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
out={'rest':{n:[list(v) for v in m] for n,m in rest.items()},'parents':{b.name:b.parent.name if b.parent else None for b in r.data.bones},'samples':{}}
for kind in ('reload','reload_empty'):
    action=bpy.data.actions['G18Auth_single_'+kind];r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
    samples=[]
    for t in (0,.08,.16,.24,.32,.48,.64,.80,.96,1.05,1.13,1.25,1.4,1.55,1.75,2.0,2.25):
        if t>action.frame_range[1]/60+.00001:continue
        frame=t*60;scene.frame_set(int(frame),subframe=frame%1);bpy.context.view_layer.update()
        g=r.pose.bones['WPN_root'].matrix;entry={'time':t}
        for n in ('hand_l','lowerarm_l','upperarm_l','WPN_SOCKET_Magazine'):
            m=g.inverted()@r.pose.bones[n].matrix;entry[n]=[list(row) for row in m]
        samples.append(entry)
    out['samples'][kind]=samples
(O/'author_inputs.json').write_text(json.dumps(out,indent=2))
for kind,samples in out['samples'].items():
    print(kind,[{'t':p['time'],'hand':[round(p['hand_l'][k][3],3) for k in range(3)],'mag':[round(p['WPN_SOCKET_Magazine'][k][3],3) for k in range(3)]} for p in samples])
