"""Retime the V13 grip/arm trajectory without solving or changing its poses."""
from pathlib import Path
import re

P = Path(__file__).resolve().parent
exec(compile((P/'author_common.py').read_text('utf-8'),str(P/'author_common.py'),'exec'))
REVISION = 'StrideRhythmUppercutV14'
timing_header = ROOT/'Source/FPSGAME/Weapons/RuneSwordUppercutMotion.h'
header = timing_header.read_text('utf-8')
timing = {k:int(re.search(r'\b'+k+r'\s*=\s*(\d+)\s*;',header)[1]) for k in
          ('SampleRate','ReleaseFrame','StrokeEndFrame','FinishFrame','RecoveryStartFrame','EndFrame')}
FPS,FRAMES = timing['SampleRate'],timing['EndFrame']
# The fast release, upright finish and short arrest retain every V13 frame.
# Only windup (96 -> 120 frames) and recover (70 -> 94 frames) are stretched.
TIME_MAP = [(0,0.),(timing['ReleaseFrame'],.8),
            (timing['RecoveryStartFrame'],128/120),(FRAMES,1.65)]
receipts = {}
for variant in ('Standard','LongGrip'):
    source = P/'SourceV13'/variant/'editable_keys.json'
    accepted = json.loads(source.read_text('utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    rig = next(o for o in scene.objects if o.type=='ARMATURE')
    rig.animation_data_clear()
    rest = {b.name:b.matrix_local.copy() for b in rig.data.bones}
    local_rest = {n:rest[PARENTS[n]].inverted()@m if PARENTS[n] in rest else m for n,m in rest.items()}
    reference = {n:canonical(native(row)) for n,row in DATA['reference'].items()}
    correction = {n:reference[n].inverted()@rest[n] for n in rest}
    rig.animation_data_create()
    action = bpy.data.actions.new('Sword_UppercutV14_'+variant)
    action.use_fake_user = True
    rig.animation_data.action = action
    samples,previous = [],{}
    for i in range(FRAMES+1):
        t = source_time(i)
        if timing['ReleaseFrame']<=i<=timing['RecoveryStartFrame']:
            keys = accepted['samples'][96+i-timing['ReleaseFrame']]['bones']
        elif i==0:keys = accepted['samples'][0]['bones']
        elif i==FRAMES:keys = accepted['samples'][-1]['bones']
        else:keys = sample_keys(accepted['samples'],t)
        samples.append(dict(seconds=i/FPS,source_seconds=t,bones=keys))
        pose = {n:canonical(m) for n,m in globalize({n:native(row) for n,row in keys.items()}).items()}
        scene.frame_set(i)
        world = {n:pose[n]@correction[n] for n in rest}
        for bone in rig.pose.bones:
            parent = world[bone.parent.name] if bone.parent else Matrix.Identity(4)
            bone.matrix_basis = local_rest[bone.name].inverted()@parent.inverted()@world[bone.name]
            bone.rotation_mode = 'QUATERNION'
            q = bone.rotation_quaternion.copy()
            if bone.name in previous and q.dot(previous[bone.name])<0:q = -q
            bone.rotation_quaternion = q
            previous[bone.name] = q.copy()
            for channel in ('location','rotation_quaternion','scale'):
                bone.keyframe_insert(channel,frame=i,group=bone.name)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation = 'LINEAR'
    scene.render.fps,scene.render.fps_base = FPS,1
    scene.frame_start,scene.frame_end = 0,FRAMES
    scene.frame_set(0)
    out = P/variant
    out.mkdir(exist_ok=True)
    patch = dict(revision=REVISION,variant=variant,source_keys=str(source),fps=FPS,
        intervals=FRAMES,seconds=FRAMES/FPS,release_seconds=timing['ReleaseFrame']/FPS,
        main_stroke_seconds=(timing['StrokeEndFrame']-timing['ReleaseFrame'])/FPS,
        finish_hold_seconds=[timing['FinishFrame']/FPS,timing['RecoveryStartFrame']/FPS],
        source_time_map=TIME_MAP,finish_blade_direction=accepted['finish_blade_direction'],samples=samples)
    (out/'editable_keys.json').write_text(json.dumps(patch,separators=(',',':')),encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'Sword_UppercutV14_Editable.blend'))
    receipts[variant] = {k:v for k,v in patch.items() if k!='samples'}
    print('UPPERCUT_V14_AUTHORED '+variant,flush=True)
(P/'authoring.json').write_text(json.dumps(dict(revision=REVISION,timing_header=str(timing_header),
    timing_frames=timing,variants=receipts,method='V13 entire-rig retiming; unchanged release/finish keys; no new grip or arm solve',
    runtime_tested=False,rendered=False,paid_motion_used=False),ensure_ascii=False,indent=2),encoding='utf-8')
