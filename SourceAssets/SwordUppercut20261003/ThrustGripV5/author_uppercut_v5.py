"""Third-combo thrust grip, adapted to a low-to-high blade sweep.

The installed thrust supplies the complete articulated pose, including finger,
wrist, elbow and twist-bone support. A shoulder-centred pitch carries that pose
through an upward cutting arc. No isolated wrist roll or new elbow IK is added.
"""
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
FPS, END = 120, 1.32
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

def delta(track,t):
    times,values = track['times'],track['values']
    k = max(0,min(len(times)-1,bisect.bisect_right(times,t)-1))
    j = min(len(times)-1,k+1)
    u = max(0.,min(1.,(t-times[k])/(times[j]-times[k]))) if j!=k else 0.
    def key(i):
        v = values[10*i:10*i+10]
        return Vector(v[:3]),Quaternion((v[6],v[3],v[4],v[5])),Vector(v[7:])
    a,b = key(k),key(j)
    return a[0].lerp(b[0],u),a[1].slerp(b[1],u),a[2].lerp(b[2],u)

def role_profile(role):
    return next((e for e in DATA.get('long_grip_profile',{}).get('clips',[])
                 if e['base'].split('.')[-1].endswith('_'+role)),None)

def live_source(variant,role,index=0):
    """Use the same base + authored deltas currently consumed by LongGrip."""
    profile = role_profile(role) if variant=='LongGrip' else None
    use_profile = profile and not profile['retained']
    e = DATA['variants']['Standard' if use_profile else variant]
    row = e['idle_world'] if role=='Idle' else e['samples'][index]['world']
    world = {n:native(r) for n,r in row.items()}
    if use_profile:
        expected = e['idle' if role=='Idle' else 'thrust']
        if profile['base']!=expected:
            raise RuntimeError('Donor profile base changed: '+profile['base'])
        local = localize(world)
        t = 0. if role=='Idle' else e['samples'][index]['seconds']
        for track in profile['tracks']:
            name = track['bone']
            dp,dq,ds = delta(track,t)
            p,q,s = local[name].decompose()
            local[name] = mat(p+dp,(dq@q).normalized(),s+ds)
        world = globalize(local)
    return {n:canonical(m) for n,m in world.items()}

def choreography(t):
    """Returns donor time, upward arm-group pitch and presentation translation.

    Pitch is about the shoulder line (screen right axis), never about the blade
    axis. The blade edge therefore sweeps low-to-high instead of being lifted
    parallel to itself. The third-hit thrust extension supplies the arm opening.
    """
    hidden = Vector((.34,-.04,-.38))
    finish = Vector((.015,.035,.015))
    if t<.42:
        u = smooth(t/.42)
        return .40*u, -60.*u, hidden*u
    if t<.48:
        return .40,-60.,hidden
    if t<.70:
        u = smooth((t-.48)/.22)
        return .40+.18*u,-60.+115.*u,hidden.lerp(finish,u)
    if t<.77:
        u = smooth((t-.70)/.07)
        return .58,55.+5.*u,finish+Vector((0,0,.012))*u
    u = smooth((t-.77)/(END-.77))
    return .58+(1.25-.58)*u,60.*(1-u),(finish+Vector((0,0,.012)))*(1-u)

receipts = {}
for variant,entry in DATA['variants'].items():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    rig = next(o for o in scene.objects if o.type=='ARMATURE')
    rig.animation_data_clear()
    rest = {b.name:b.matrix_local.copy() for b in rig.data.bones}
    local_rest = {n:rest[PARENTS[n]].inverted()@m if PARENTS[n] in rest else m for n,m in rest.items()}
    reference = {n:canonical(native(row)) for n,row in DATA['reference'].items()}
    correction = {n:reference[n].to_quaternion().inverted()@rest[n].to_quaternion() for n in rest}
    idle = live_source(variant,'Idle')
    donor = [localize(live_source(variant,'Thrust',i)) for i in range(len(entry['samples']))]
    pivot = (idle['upperarm_l'].translation+idle['upperarm_r'].translation)*.5
    def sample(t):
        f = max(0.,min(len(donor)-1,t*120))
        a,b = int(f),min(len(donor)-1,int(f)+1)
        return globalize({n:blend(donor[a][n],donor[b][n],f-a) for n in NAMES})
    rig.animation_data_create()
    action = bpy.data.actions.new('Sword_UppercutV5_'+variant)
    action.use_fake_user = True
    rig.animation_data.action = action
    samples,previous,blend_previous = [],{},{}
    for i in range(FRAMES+1):
        t = i/FPS
        source_t,pitch,shift = choreography(t)
        rotation = Quaternion((1,0,0),math.radians(pitch))
        carry = Matrix.Translation(pivot+shift)@rotation.to_matrix().to_4x4()@Matrix.Translation(-pivot)
        pose = {n:carry@m for n,m in sample(source_t).items()}
        if i in (0,FRAMES):pose = {n:m.copy() for n,m in idle.items()}
        ue = {n:mat(C@m.translation*100,(C@m.to_quaternion().to_matrix()@C).to_quaternion(),m.to_scale())
              for n,m in pose.items()}
        keys = {}
        for n,local in localize(ue).items():
            p,q,s = local.decompose()
            if n in previous and q.dot(previous[n])<0:q = -q
            previous[n] = q.copy()
            keys[n] = dict(p=list(p),q=list(q),s=list(s))
        samples.append(dict(seconds=t,bones=keys))
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
    patch = dict(revision='ThrustGripRisingCutV5',variant=variant,source_idle=entry['idle'],
        source_thrust=entry['thrust'],fps=FPS,intervals=FRAMES,seconds=END,samples=samples)
    (out/'editable_keys.json').write_text(json.dumps(patch,separators=(',',':')),encoding='utf-8')
    blend_path = out/'Sword_UppercutV5_Editable.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    receipts[variant] = dict(blend=str(blend_path),keys=str(out/'editable_keys.json'),seconds=END,
        source_thrust=entry['thrust'],shoulder_pivot_m=list(pivot),
        hand_and_joint_processing='Current third-hit thrust articulation transported as a complete group',
        long_grip_source='Current playback profile' if variant=='LongGrip' else None)
    print('THRUST_GRIP_UPPERCUT_V5_AUTHORED '+variant,flush=True)
(P/'authoring.json').write_text(json.dumps(dict(revision='ThrustGripRisingCutV5',fps=FPS,
    sources='Current installed third-combo thrust and live LongGrip profile; user-directed rising cut',
    paid_motion_used=False,phases=dict(lower_right=[0,.42],hold=[.42,.48],cut=[.48,.70],
        follow_through=[.70,.77],recover=[.77,END]),variants=receipts,
    runtime_tested=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf-8')
