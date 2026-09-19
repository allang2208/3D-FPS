"""Requested, scoped source check: right wrist, preserved tracks and transitions."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
report={}
for profile in ('Base','Drum','Angled','Vertical','Canted','Prism'):
    bpy.ops.wm.open_mainfile(filepath=str(P/profile/f'M4_QuickCombat_{profile}_Editable.blend'))
    rig=bpy.data.objects['SK_M4_Infima']; scene=bpy.context.scene
    rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
    restfore=(rest['hand_r'].translation-rest['lowerarm_r'].translation).normalized()
    fingers={b.name for b in rig.data.bones['hand_r'].children_recursive}
    left={'clavicle_l'}|{b.name for b in rig.data.bones['clavicle_l'].children_recursive}
    preserved=left|{n for n in rest if n.startswith('WPN_')}
    frames=[i*.5 for i in range(217)]
    values={}
    for rev in ('K','N'):
        a=bpy.data.actions[f'M4_QuickCombatRefine{rev}_{profile}']; rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
        rows=[]
        for f in frames:
            scene.frame_set(int(f),subframe=f-int(f)); bpy.context.view_layer.update()
            rows.append(({b.name:b.matrix.copy() for b in rig.pose.bones},{n:rig.pose.bones[n].matrix_basis.copy() for n in fingers}))
        values[rev]=rows
    out={'samples':len(frames),'max_preserved_position_mm':0.,'max_preserved_rotation_deg':0.,
         'max_finger_local_matrix_difference':0.,'max_segment_length_difference_mm':0.,
         'max_wrist_axis_bend_deg':0.,'max_right_hand_rotation_step_deg_at_240hz':0.,'max_right_elbow_step_mm_at_240hz':0.,
         'max_endpoint_matrix_difference':0.,'max_K_elbow_step_mm_at_240hz':0.,'largest_elbow_step_frame':0.,'key_poses':[]}
    for i,(frame_number,(n,nf),(k,kf)) in enumerate(zip(frames,values['N'],values['K'])):
        for name in preserved:
            out['max_preserved_position_mm']=max(out['max_preserved_position_mm'],1000*(n[name].translation-k[name].translation).length)
            q=n[name].to_quaternion().rotation_difference(k[name].to_quaternion()); a=2*math.atan2(Vector((q.x,q.y,q.z)).length,abs(q.w))
            out['max_preserved_rotation_deg']=max(out['max_preserved_rotation_deg'],math.degrees(a))
        for name in fingers:
            out['max_finger_local_matrix_difference']=max(out['max_finger_local_matrix_difference'],max(abs(nf[name][a][b]-kf[name][a][b]) for a in range(4) for b in range(4)))
        for start,end in (('upperarm_r','lowerarm_r'),('lowerarm_r','hand_r')):
            delta=abs((n[end].translation-n[start].translation).length-(k[end].translation-k[start].translation).length)
            out['max_segment_length_difference_mm']=max(out['max_segment_length_difference_mm'],1000*delta)
        fore=n['hand_r'].translation-n['lowerarm_r'].translation
        desired=n['hand_r'].to_quaternion() @ rest['hand_r'].to_quaternion().inverted() @ restfore
        bend=math.degrees(fore.angle(desired));out['max_wrist_axis_bend_deg']=max(out['max_wrist_axis_bend_deg'],bend)
        if i:
            prev=values['N'][i-1][0]
            q=n['hand_r'].to_quaternion().rotation_difference(prev['hand_r'].to_quaternion())
            a=math.degrees(2*math.atan2(Vector((q.x,q.y,q.z)).length,abs(q.w)))
            out['max_right_hand_rotation_step_deg_at_240hz']=max(out['max_right_hand_rotation_step_deg_at_240hz'],a)
            step=1000*(n['lowerarm_r'].translation-prev['lowerarm_r'].translation).length
            if step>out['max_right_elbow_step_mm_at_240hz']:
                out['max_right_elbow_step_mm_at_240hz']=step;out['largest_elbow_step_frame']=frame_number
            kp=values['K'][i-1][0]
            out['max_K_elbow_step_mm_at_240hz']=max(out['max_K_elbow_step_mm_at_240hz'],1000*(k['lowerarm_r'].translation-kp['lowerarm_r'].translation).length)
        if frame_number in (0,8,12,16,20,32,72,96,108):out['key_poses'].append({'frame':frame_number,'wrist_bend_deg':bend})
        if frame_number in (0,108):
            out['max_endpoint_matrix_difference']=max(out['max_endpoint_matrix_difference'],max(abs(n[name][a][b]-k[name][a][b]) for name in n for a in range(4) for b in range(4)))
    report[profile]=out
    print('SOURCE_CHECK',profile,json.dumps(out),flush=True)
(P/'source_checks.json').write_text(json.dumps(report,indent=2))
