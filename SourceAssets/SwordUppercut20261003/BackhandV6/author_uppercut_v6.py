"""Backhand rising cut with a visible palm/forearm turnover.

The installed second slash supplies the complete articulated forearm turn and
reverse cutting arc. The blade stays on the thumb side of each closed hand.
No ice-pick regrip, isolated wrist roll or new elbow IK is added.
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
FPS, END = 120, 1.50
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
    rows = e['samples'] if role=='Thrust' else (e['slashes'][role]['samples'] if role!='Idle' else None)
    row = e['idle_world'] if role=='Idle' else rows[index]['world']
    world = {n:native(r) for n,r in row.items()}
    if use_profile:
        expected = e['idle' if role=='Idle' else 'thrust'] if role in ('Idle','Thrust') else e['slashes'][role]['asset']
        if profile['base']!=expected:
            raise RuntimeError('Donor profile base changed: '+profile['base'])
        local = localize(world)
        t = 0. if role=='Idle' else rows[index]['seconds']
        for track in profile['tracks']:
            name = track['bone']
            dp,dq,ds = delta(track,t)
            p,q,s = local[name].decompose()
            local[name] = mat(p+dp,(dq@q).normalized(),s+ds)
        world = globalize(local)
    return {n:canonical(m) for n,m in world.items()}

def choreography(t,duration):
    """First show the hand turn; only then hide the sword and make the cut.

    Reverse the source's return to obtain its supported palm/forearm turnover.
    Reverse its actual cutting section to turn a downstroke into an upstroke.
    The source's stationary 0.65..0.85 load is skipped during our final return.
    """
    visible = Vector((0,.025,0))
    hidden = Vector((.14,.06,-.24))
    release = Vector((0,.03,.005))
    if t<.34:
        u = smooth(t/.34)
        return duration+(1.44-duration)*u,visible*u
    if t<.52:
        u = smooth((t-.34)/.18)
        return 1.44+(.95-1.44)*u,visible.lerp(hidden,u)
    if t<.60:
        return .95,hidden
    if t<.80:
        u = smooth((t-.60)/.20)
        return .95-.05*u,hidden.lerp(release,u)
    if t<.88:
        u = smooth((t-.80)/.08)
        return .90-.015*u,release
    if t<.98:
        u = smooth((t-.88)/.10)
        return .885-.035*u,release
    u = smooth((t-.98)/(END-.98))
    return .65*(1-u),release*(1-u)

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
    clip = entry['slashes']['Slash2']
    donor = [localize(live_source(variant,'Slash2',i)) for i in range(len(clip['samples']))]
    def sample(t):
        f = max(0.,min(len(donor)-1,t/clip['seconds']*(len(donor)-1)))
        a,b = int(f),min(len(donor)-1,int(f)+1)
        return globalize({n:blend(donor[a][n],donor[b][n],f-a) for n in NAMES})
    rig.animation_data_create()
    action = bpy.data.actions.new('Sword_UppercutV6_'+variant)
    action.use_fake_user = True
    rig.animation_data.action = action
    samples,previous,blend_previous = [],{},{}
    for i in range(FRAMES+1):
        t = i/FPS
        source_t,shift = choreography(t,clip['seconds'])
        carry = Matrix.Translation(shift)
        # The native source supplies ALL rotations: palm turn, pronation,
        # elbow movement, helper-bone support and blade edge orientation.
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
    patch = dict(revision='BackhandPalmTurnUppercutV6',variant=variant,source_idle=entry['idle'],
        source_motion=clip['asset'],fps=FPS,intervals=FRAMES,seconds=END,samples=samples)
    (out/'editable_keys.json').write_text(json.dumps(patch,separators=(',',':')),encoding='utf-8')
    blend_path = out/'Sword_UppercutV6_Editable.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    receipts[variant] = dict(blend=str(blend_path),keys=str(out/'editable_keys.json'),seconds=END,
        source_motion=clip['asset'],hand_and_joint_processing='Native articulated forearm/palm turn and reversed rising cut',
        long_grip_source='Current playback profile' if variant=='LongGrip' else None)
    print('BACKHAND_UPPERCUT_V6_AUTHORED '+variant,flush=True)
(P/'authoring.json').write_text(json.dumps(dict(revision='BackhandPalmTurnUppercutV6',fps=FPS,
    sources='Current installed Slash2 articulation and live LongGrip profile; user-directed backhand rising cut',
    grip='Blade remains on thumb side; closed-finger grip; no inverted/ice-pick regrip',
    paid_motion_used=False,phases=dict(visible_palm_turn=[0,.34],lower_right=[.34,.52],hold=[.52,.60],
        upward_cut=[.60,.80],follow_through=[.80,.88],unload=[.88,.98],recover=[.98,END]),
    variants=receipts,runtime_tested=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf-8')

