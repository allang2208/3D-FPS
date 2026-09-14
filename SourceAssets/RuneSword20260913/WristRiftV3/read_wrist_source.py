import bpy,json,math
from pathlib import Path
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'ReachSweepV2/AzureRunesword_Manny_Editable.blend'))
r=bpy.data.objects['SK_RuneSword_Rig'];s=bpy.context.scene
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
out={'rest':{},'poses':{}}
for n in rest:
    if n.startswith(('hand_','upperarm','lowerarm','clavicle_')):
        out['rest'][n]={'parent':r.data.bones[n].parent.name,'head':list(rest[n].translation)}
for clip,frames in [('Idle',[0]),('Slash1',[0,22,28,40,55,66,80]),('Slash2',[22,28,40,55,65])]:
    act=bpy.data.actions['A_RuneSword_'+clip];r.animation_data.action=act;r.animation_data.action_slot=act.slots[0]
    for f in frames:
        s.frame_set(f);row={}
        for side in ['l','r']:
            un,fn,hn=[n+'_'+side for n in ['upperarm','lowerarm','hand']]
            H=r.pose.bones[hn].matrix;F=r.pose.bones[fn].matrix
            fd=(H.translation-F.translation).normalized()
            old=(rest[hn].translation-rest[fn].translation).normalized()
            hd=(H.to_quaternion()@rest[hn].to_quaternion().inverted())@old
            row[side]={'bend_degrees':math.degrees(fd.angle(hd)), 'hand_direction':list(hd),
                'hand_position':list(H.translation),'elbow_position':list(F.translation)}
        out['poses'][clip+'_'+str(f)]=row
(P/'wrist_source.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out['poses'],indent=2))
