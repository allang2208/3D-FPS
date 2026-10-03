"""Retime the complete V8 pose: deliberate lower-right windup, held anticipation, then a twice-speed rising cut."""
import bisect
import json
import math
from pathlib import Path
import bpy
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
DATA = json.loads((P/'inputs.json').read_text('utf-8'))
SOURCE = ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/RuneSword_BareArmsV7.blend'
FPS, END = 120, 1.70
FRAMES = round(FPS*END)
END = FRAMES/FPS
C = Matrix.Diagonal(Vector((1,-1,1)))
NAMES = list(DATA['parents'])
PARENTS = DATA['parents']

def mat(p,q,s=(1,1,1)):
    return Matrix.LocRotScale(Vector(p),q,Vector(s))

def native(row):
    return mat(row['p'],Quaternion(row['q']),row['s'])

def canonical(m):
    p,q,s = m.decompose()
    return mat(C@p*.01,(C@q.to_matrix()@C).to_quaternion(),s)

def localize(world):
    return {n:world[PARENTS[n]].inverted()@world[n] if PARENTS[n] in world else world[n] for n in NAMES}

def globalize(local):
    world = {}
    def get(n):
        if n not in world:
            parent = PARENTS[n]
            world[n] = get(parent)@local[n] if parent in local else local[n].copy()
        return world[n]
    for n in NAMES:get(n)
    return world

def blend(a,b,u):
    pa,qa,sa = a.decompose()
    pb,qb,sb = b.decompose()
    return mat(pa.lerp(pb,u),qa.slerp(qb,u),sa.lerp(sb,u))

def smooth(x):
    x = max(0.,min(1.,x))
    return x*x*x*(10+x*(-15+6*x))

# New 120 Hz frame -> V8 seconds. Release and follow-through share one slope
# so the blade keeps its speed at the transition through the main strike.
TIME_MAP = [(0,0.),(32,.32),(80,.54),(96,.60),(116,.94),(126,1.06),(204,1.70)]

def source_time(frame):
    for a,b in zip(TIME_MAP,TIME_MAP[1:]):
        if frame<=b[0]:
            u = (frame-a[0])/(b[0]-a[0])
            return a[1]+(b[1]-a[1])*u
    return TIME_MAP[-1][1]

def interpolated_pose(clip,t):
    source = clip['samples']
    position = max(0.,min(len(source)-1,t*clip['fps']))
    a,b = int(position),min(len(source)-1,int(position)+1)
    u = position-a
    if u<1.e-7:
        return {n:dict(k) for n,k in source[a]['bones'].items()}
    result = {}
    for n,x in source[a]['bones'].items():
        y = source[b]['bones'][n]
        qa,qb = Quaternion(x['q']),Quaternion(y['q'])
        if qa.dot(qb)<0:qb = -qb
        result[n] = dict(p=list(Vector(x['p']).lerp(Vector(y['p']),u)),
                         q=list(qa.slerp(qb,u)),s=list(Vector(x['s']).lerp(Vector(y['s']),u)))
    return result

receipts = {}
for variant in DATA['variants']:
    source_keys = P/'SourceV8'/variant/'editable_keys.json'
    source_clip = json.loads(source_keys.read_text('utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    rig = next(o for o in scene.objects if o.type=='ARMATURE')
    rig.animation_data_clear()
    rest = {b.name:b.matrix_local.copy() for b in rig.data.bones}
    local_rest = {n:rest[PARENTS[n]].inverted()@m if PARENTS[n] in rest else m for n,m in rest.items()}
    reference = {n:canonical(native(row)) for n,row in DATA['reference'].items()}
    correction = {n:reference[n].to_quaternion().inverted()@rest[n].to_quaternion() for n in rest}
    rig.animation_data_create()
    action = bpy.data.actions.new('Sword_UppercutV9_'+variant)
    action.use_fake_user = True
    rig.animation_data.action = action
    samples,previous,blend_previous = [],{},{}
    for i in range(FRAMES+1):
        src_t = source_time(i)
        keys = interpolated_pose(source_clip,src_t)
        for n,row in keys.items():
            q = Quaternion(row['q'])
            if n in previous and q.dot(previous[n])<0:q = -q
            row['q'] = list(q)
            previous[n] = q.copy()
        samples.append(dict(seconds=i/FPS,source_seconds=src_t,bones=keys))
        pose = {n:canonical(m) for n,m in globalize({n:native(k) for n,k in keys.items()}).items()}
        scene.frame_set(i)
        worlds = {n:mat(pose[n].translation,pose[n].to_quaternion()@correction[n],pose[n].to_scale()) for n in rest}
        for bone in rig.pose.bones:
            parent_world = worlds[bone.parent.name] if bone.parent else Matrix.Identity(4)
            bone.matrix_basis = local_rest[bone.name].inverted()@parent_world.inverted()@worlds[bone.name]
            bone.rotation_mode = 'QUATERNION'
            q = bone.rotation_quaternion.copy()
            if bone.name in blend_previous and q.dot(blend_previous[bone.name])<0:q = -q
            bone.rotation_quaternion = q
            blend_previous[bone.name] = q.copy()
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
    patch = dict(revision='ChargedSnapUppercutV9',variant=variant,source_keys=str(source_keys),
                 fps=FPS,intervals=FRAMES,seconds=END,time_map=TIME_MAP,samples=samples)
    (out/'editable_keys.json').write_text(json.dumps(patch,separators=(',',':')),encoding='utf-8')
    blend_path = out/'Sword_UppercutV9_Editable.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    receipts[variant] = dict(blend=str(blend_path),keys=str(out/'editable_keys.json'),seconds=END)
    print('CHARGED_SNAP_UPPERCUT_V9_AUTHORED '+variant,flush=True)
(P/'authoring.json').write_text(json.dumps(dict(revision='ChargedSnapUppercutV9',fps=FPS,
    request='Wind up toward lower-right, then suddenly slash upward faster',
    processing='One time mapping for every V8 bone; original grip, contact, arm support and blade path retained',
    time_map=[dict(frame=f,seconds=f/FPS,source_seconds=t) for f,t in TIME_MAP],
    lower_right_seconds=.4,held_windup_seconds=16/FPS,release_speed_multiplier=2.04,
    main_strike_seconds=.23/2.04,follow_seconds=.11/2.04,
    variants=receipts,paid_motion_used=False,runtime_tested=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf-8')

