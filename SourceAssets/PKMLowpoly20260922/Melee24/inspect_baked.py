"""Check the requested grip and return constraints on the actual baked actions."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
grips=json.loads((O/'grips.json').read_text());out={}
for family,data in grips.items():
    bpy.ops.wm.open_mainfile(filepath=str(O/f'PKM_{family}_Melee24.blend'),use_scripts=False)
    r=bpy.data.objects['PKM_Manny_Rig'];s=bpy.context.scene
    a=bpy.data.actions[f'PKM24_{family}_quick_melee'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
    idle={n:Matrix(v) for n,v in data['idle'].items()};parents=data['parents']
    reference={side:idle['WPN_root'].inverted()@idle['hand_'+side] for side in 'rl'}
    vals={'max_grip_position_error_mm':0.,'max_grip_rotation_error_deg':0.,'max_finger_rotation_error_deg':0.,
          'max_bone_length_error_mm':0.,'endpoint_max_bone_position_error_mm':0.,'endpoint_max_bone_rotation_error_deg':0.}
    for f in range(217):
        s.frame_set(f);bpy.context.view_layer.update();p={b.name:b.matrix.copy() for b in r.pose.bones}
        for side in 'rl':
            rel=p['WPN_root'].inverted()@p['hand_'+side]
            vals['max_grip_position_error_mm']=max(vals['max_grip_position_error_mm'],1000*(rel.translation-reference[side].translation).length)
            vals['max_grip_rotation_error_deg']=max(vals['max_grip_rotation_error_deg'],math.degrees(rel.to_quaternion().rotation_difference(reference[side].to_quaternion()).angle))
            for start,end in [('upperarm','lowerarm'),('lowerarm','hand')]:
                old=(idle[end+'_'+side].translation-idle[start+'_'+side].translation).length
                current=(p[end+'_'+side].translation-p[start+'_'+side].translation).length
                vals['max_bone_length_error_mm']=max(vals['max_bone_length_error_mm'],1000*abs(current-old))
        for n in p:
            if n.startswith(('index_','middle_','ring_','pinky_','thumb_')):
                old=idle[parents[n]].inverted()@idle[n];current=p[parents[n]].inverted()@p[n]
                angle=math.degrees(current.to_quaternion().rotation_difference(old.to_quaternion()).angle)
                vals['max_finger_rotation_error_deg']=max(vals['max_finger_rotation_error_deg'],min(angle,360-angle))
            if f in (0,216):
                vals['endpoint_max_bone_position_error_mm']=max(vals['endpoint_max_bone_position_error_mm'],1000*(p[n].translation-idle[n].translation).length)
                angle=math.degrees(p[n].to_quaternion().rotation_difference(idle[n].to_quaternion()).angle)
                vals['endpoint_max_bone_rotation_error_deg']=max(vals['endpoint_max_bone_rotation_error_deg'],min(angle,360-angle))
    out[family]=vals
    print('PKM24_BAKED_CONTACT',family,json.dumps(vals),flush=True)
(O/'baked_inspection.json').write_text(json.dumps(out,indent=2))
