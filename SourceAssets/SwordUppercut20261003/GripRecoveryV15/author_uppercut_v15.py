"""Keep contact around the hilt during entry/recovery; refine the left support."""
from pathlib import Path
import re
P=Path(__file__).resolve().parent
exec(compile((P/'arm_support.py').read_text('utf-8'),str(P/'arm_support.py'),'exec'))
REVISION='GripRecoveryUppercutV15'
header=(ROOT/'Source/FPSGAME/Weapons/RuneSwordUppercutMotion.h').read_text('utf-8')
timing={k:int(re.search(r'\b'+k+r'\s*=\s*(\d+)\s*;',header)[1]) for k in
        ('SampleRate','ReleaseFrame','StrokeEndFrame','FinishFrame','RecoveryStartFrame','EndFrame')}
FPS,FRAMES=timing['SampleRate'],timing['EndFrame']
RELEASE,RECOVERY,END=[timing[k]/FPS for k in ('ReleaseFrame','RecoveryStartFrame','EndFrame')]

def rigid(m):return mat(m.translation,m.to_quaternion())

def blend(a,b,u):
    p,q,s=a.decompose();r,v,k=b.decompose()
    if q.dot(v)<0:v=-v
    return mat(p.lerp(r,u),q.slerp(v,u),s.lerp(k,u))

def blend_rows(a,b,u):
    return {n:blend(native(a[n]),native(b[n]),u) for n in NAMES}

def serialize(pose,previous):
    ue={n:mat(C@m.translation*100,(C@m.to_quaternion().to_matrix()@C).to_quaternion(),m.to_scale()) for n,m in pose.items()}
    result={}
    for n,m in localize(ue).items():
        p,q,s=m.decompose()
        if n in previous and q.dot(previous[n])<0:q=-q
        previous[n]=q.copy()
        result[n]=dict(p=list(p),q=list(q),s=list(s))
    return result

receipts={}
for variant in ('Standard','LongGrip'):
    source=P/'SourceV14'/variant/'editable_keys.json'
    accepted=json.loads(source.read_text('utf-8'))
    idle=pose_from_rows(accepted['samples'][0]['bones'])
    low=pose_from_rows(accepted['samples'][timing['ReleaseFrame']]['bones'])
    hold=pose_from_rows(accepted['samples'][timing['RecoveryStartFrame']]['bones'])
    idle_rows=accepted['samples'][0]['bones']
    low_rows=accepted['samples'][timing['ReleaseFrame']]['bones']
    hold_rows=accepted['samples'][timing['RecoveryStartFrame']]['bones']
    grip={s:rigid(idle['WPN_root']).inverted()@rigid(idle['hand_'+s]) for s in ('l','r')}
    turns={}
    for s in ('l','r'):
        a=grip[s].translation
        b=(rigid(low['WPN_root']).inverted()@rigid(low['hand_'+s])).translation
        turns[s]=math.atan2(math.sin(math.atan2(b.y,b.x)-math.atan2(a.y,a.x)),
                            math.cos(math.atan2(b.y,b.x)-math.atan2(a.y,a.x)))
    # Small roll about the actual hilt axis; no thumb/pinky order reversal.
    turns['l']+=math.radians(8.)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene
    rig=next(o for o in scene.objects if o.type=='ARMATURE')
    rig.animation_data_clear()
    rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
    local_rest={n:rest[PARENTS[n]].inverted()@m if PARENTS[n] in rest else m for n,m in rest.items()}
    reference={n:canonical(native(row)) for n,row in DATA['reference'].items()}
    correction={n:reference[n].inverted()@rest[n] for n in rest}
    stations={s:fit_skin_stations([o for o in scene.objects if o.type=='MESH'],reference,s) for s in ('l','r')}
    states={s:dict(pole=0.,roll=0.) for s in ('l','r')}
    rig.animation_data_create()
    action=bpy.data.actions.new('Sword_UppercutV15_'+variant)
    action.use_fake_user=True
    rig.animation_data.action=action
    samples,previous,blend_previous=[],{},{}
    for i in range(FRAMES+1):
        t=i/FPS
        original=accepted['samples'][i]['bones']
        original_pose=pose_from_rows(original)
        if i<timing['ReleaseFrame']:
            u=smooth(t/.88)
            base={n:canonical(m) for n,m in globalize(blend_rows(idle_rows,low_rows,u)).items()}
            weapon=blend(idle['WPN_root'],low['WPN_root'],u)
            grasp_weight=u
            right_support=smooth(t/.12)*(1.-smooth((t-.75)/.25))
        elif i<=timing['RecoveryStartFrame']:
            base=original_pose
            weapon=base['WPN_root'].copy()
            grasp_weight=1.
            right_support=0.
        else:
            u=smooth((t-RECOVERY)/(END-RECOVERY))
            base={n:canonical(m) for n,m in globalize(blend_rows(hold_rows,idle_rows,u)).items()}
            weapon=blend(hold['WPN_root'],idle['WPN_root'],u)
            grasp_weight=1.-u
            right_support=smooth((t-RECOVERY)/.12)*(1.-smooth((t-(END-.18))/.18))
        pose={n:m.copy() for n,m in base.items()}
        carry=weapon@base['WPN_root'].inverted()
        for n in descendants('WPN_root')|{'ik_hand_gun'}:pose[n]=carry@base[n]
        for s in ('l','r'):
            hand='hand_'+s
            # Preserve the accepted right hand/arm through the complete strike.
            if s=='r' and timing['ReleaseFrame']<=i<=timing['RecoveryStartFrame']:
                continue
            rotation=Quaternion(Vector((0,0,1)),turns[s]*grasp_weight)
            h=rigid(weapon)@rotation.to_matrix().to_4x4()@grip[s]
            target=mat(h.translation,h.to_quaternion(),base[hand].to_scale())
            hand_carry=target@base[hand].inverted()
            for n in HANDS[s]:pose[n]=hand_carry@base[n]
        # Both wrists stay constrained; shoulders/elbows supply the motion.
        # The left solver prioritizes wrist support, with continuous pole/roll.
        left_support=smooth(t/.12)*(1.-smooth((t-(END-.18))/.18))
        solve_supported_arm(pose,idle,base,'l',left_support,states['l'],stations['l'])
        solve_supported_arm(pose,idle,base,'r',right_support,states['r'],stations['r'])
        for s in ('l','r'):
            pose['ik_hand_'+s]=pose['hand_'+s]@idle['hand_'+s].inverted()@idle['ik_hand_'+s]
        if i in (0,FRAMES):pose={n:m.copy() for n,m in idle.items()}
        keys=serialize(pose,previous)
        if i in (0,FRAMES):keys=idle_rows
        samples.append(dict(seconds=t,bones=keys))
        scene.frame_set(i)
        world={n:pose[n]@correction[n] for n in rest}
        for bone in rig.pose.bones:
            parent=world[bone.parent.name] if bone.parent else Matrix.Identity(4)
            bone.matrix_basis=local_rest[bone.name].inverted()@parent.inverted()@world[bone.name]
            bone.rotation_mode='QUATERNION'
            q=bone.rotation_quaternion.copy()
            if bone.name in blend_previous and q.dot(blend_previous[bone.name])<0:q=-q
            bone.rotation_quaternion=q
            blend_previous[bone.name]=q.copy()
            for channel in ('location','rotation_quaternion','scale'):bone.keyframe_insert(channel,frame=i,group=bone.name)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    scene.render.fps,scene.render.fps_base=FPS,1
    scene.frame_start,scene.frame_end=0,FRAMES
    scene.frame_set(0)
    out=P/variant
    out.mkdir(exist_ok=True)
    patch=dict(revision=REVISION,variant=variant,source_keys=str(source),fps=FPS,intervals=FRAMES,
        seconds=END,release_seconds=RELEASE,main_stroke_seconds=(timing['StrokeEndFrame']-timing['ReleaseFrame'])/FPS,
        finish_blade_direction=accepted['finish_blade_direction'],grip_turn_degrees={s:math.degrees(a) for s,a in turns.items()},
        method='Circular hilt contact for both wrists; rigid weapon return; supported arm solve; left hilt roll adjustment +8 degrees',samples=samples)
    (out/'editable_keys.json').write_text(json.dumps(patch,separators=(',',':')),encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'Sword_UppercutV15_Editable.blend'))
    receipts[variant]={k:v for k,v in patch.items() if k!='samples'}
    print('UPPERCUT_V15_AUTHORED '+variant,flush=True)
(P/'authoring.json').write_text(json.dumps(dict(revision=REVISION,variants=receipts,runtime_tested=False,
    paid_motion_used=False),ensure_ascii=False,indent=2),encoding='utf-8')
