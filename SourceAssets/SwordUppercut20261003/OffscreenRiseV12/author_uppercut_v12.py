"""Author offscreen windup, higher two-hand rise and a 75 ms release from V11."""
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
FPS, FRAMES = 120, 198
C = Matrix.Diagonal(Vector((1,-1,1)))
PARENTS = DATA['parents']
NAMES = list(PARENTS)
TIME_MAP = [(0,0.),(32,32/120),(80,80/120),(96,.8),
            (105,.9127450980392157),(111,116/120),(120,1.05),(198,1.70)]

def mat(p,q,s=(1,1,1)):
    return Matrix.LocRotScale(Vector(p),q,Vector(s))

def native(row):
    return mat(row['p'],Quaternion(row['q']),row['s'])

def canonical(m):
    p,q,s = m.decompose()
    return mat(C@p*.01,(C@q.to_matrix()@C).to_quaternion(),s)

def globalize(local):
    world = {}
    def get(n):
        if n not in world:
            parent = PARENTS[n]
            world[n] = get(parent)@local[n] if parent in local else local[n].copy()
        return world[n]
    for n in NAMES:get(n)
    return world

def localize(world):
    return {n:world[PARENTS[n]].inverted()@world[n] if PARENTS[n] in world else world[n] for n in NAMES}

def descendants(name):
    result = {name}
    for n in NAMES:
        parent = PARENTS[n]
        while parent in PARENTS:
            if parent==name:
                result.add(n)
                break
            parent = PARENTS[parent]
    return result

HANDS = {side:descendants('hand_'+side) for side in ('l','r')}
WEAPON = descendants('WPN_root') | {'ik_hand_l','ik_hand_r'}

def smooth(x):
    x = max(0.,min(1.,x))
    return x*x*x*(10+x*(-15+6*x))

def source_time(frame):
    for (a,ta),(b,tb) in zip(TIME_MAP,TIME_MAP[1:]):
        if frame<=b:return ta+(tb-ta)*(frame-a)/(b-a)
    return TIME_MAP[-1][1]

def sample_keys(samples,t):
    times = [e['seconds'] for e in samples]
    k = max(0,min(len(times)-1,bisect.bisect_right(times,t)-1))
    j = min(len(times)-1,k+1)
    alpha = (t-times[k])/(times[j]-times[k]) if j!=k else 0.
    a,b = samples[k]['bones'],samples[j]['bones']
    result = {}
    for n in NAMES:
        qa,qb = Quaternion(a[n]['q']),Quaternion(b[n]['q'])
        if qa.dot(qb)<0:qb = -qb
        result[n] = dict(p=list(Vector(a[n]['p']).lerp(Vector(b[n]['p']),alpha)),
                         q=list(qa.slerp(qb,alpha)),
                         s=list(Vector(a[n]['s']).lerp(Vector(b[n]['s']),alpha)))
    return result

def limb_frame(direction,normal):
    x = direction.normalized()
    z = (normal-x*normal.dot(x)).normalized()
    return Matrix((x,z.cross(x).normalized(),z)).transposed()

def raise_supported_arm(pose,base,side):
    """Transport the V11 elbow plane; retain hand orientation and bone lengths."""
    name = lambda stem:stem+'_'+side
    s0,e0,h0 = (base[name(n)].translation for n in ('upperarm','lowerarm','hand'))
    h = pose[name('hand')].translation
    upper0,fore0 = e0-s0,h0-e0
    first,second = upper0.length,fore0.length
    u0 = (h0-s0).normalized()
    pole0 = e0-s0-u0*(e0-s0).dot(u0)
    s = s0.copy()
    reach = h-s
    maximum = (first+second)*.97
    if reach.length>maximum:s += reach.normalized()*(reach.length-maximum)
    distance = (h-s).length
    axis = (h-s).normalized()
    pole = u0.rotation_difference(axis)@pole0.normalized()
    pole = (pole-axis*pole.dot(axis)).normalized()
    along = (first*first-second*second+distance*distance)/(2*distance)
    e = s+axis*along+pole*math.sqrt(max(0.,first*first-along*along))
    upper,fore = e-s,h-e
    plane0,plane = upper0.cross(fore0).normalized(),upper.cross(fore).normalized()
    du = (limb_frame(upper,plane)@limb_frame(upper0,plane0).transposed()).to_quaternion()
    df = (limb_frame(fore,plane)@limb_frame(fore0,plane0).transposed()).to_quaternion()
    for stem,position,dq in (('upperarm',s,du),('lowerarm',e,df)):
        n = name(stem)
        pose[n] = mat(position,dq@base[n].to_quaternion(),base[n].to_scale())
    # The hand has no new roll. Distribute the forearm's hinge change by station
    # instead of rotating the entire upper arm to match a palm normal.
    distal = fore0.normalized().rotation_difference(fore.normalized())
    if df.dot(distal)<0:distal = -distal
    for number in ('01','02'):
        n = name('lowerarm_twist_'+number)
        station = max(0.,min(1.,(base[n].translation-e0).dot(fore0.normalized())/second))
        pose[n] = mat(e+df@(base[n].translation-e0),df.slerp(distal,station)@base[n].to_quaternion(),base[n].to_scale())
        n = name('upperarm_twist_'+number)
        pose[n] = mat(s+du@(base[n].translation-s0),du@base[n].to_quaternion(),base[n].to_scale())
    pose[name('clavicle')] = Matrix.Translation(s-s0)@base[name('clavicle')]

receipts = {}
for variant in ('Standard','LongGrip'):
    source = P/'SourceV11'/variant/'editable_keys.json'
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

    def apply_blender(pose):
        # Full bind correction includes the native UE 100x skeleton scale.
        # UE keys retain that scale; Blender skinning uses its metre-space bind.
        worlds = {n:pose[n]@correction[n] for n in rest}
        for bone in rig.pose.bones:
            parent_world = worlds[bone.parent.name] if bone.parent else Matrix.Identity(4)
            bone.matrix_basis = local_rest[bone.name].inverted()@parent_world.inverted()@worlds[bone.name]
            bone.rotation_mode = 'QUATERNION'

    # Size the offscreen translation from the actual source arm surface and
    # the blade/pommel envelope. This is authoring geometry, not a runtime test.
    # .88 is wider than tan(75deg/2); another 10 cm covers clothing/guard width.
    highest = -100.
    meshes = [o for o in scene.objects if o.type=='MESH']
    for i in range(32,97,4):
        rows = accepted['samples'][i]['bones']
        pose = {n:canonical(m) for n,m in globalize({n:native(k) for n,k in rows.items()}).items()}
        apply_blender(pose)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        points = []
        for obj in meshes:
            evaluated = obj.evaluated_get(dg)
            points.extend(evaluated.matrix_world@v.co for v in evaluated.data.vertices)
        points.extend(pose[n].translation for n in WEAPON)
        highest = max(highest,max(v.z+.88*max(0.,v.y) for v in points))
    offscreen = Vector((.24,0.,-max(.38,highest+.10)))
    rig.animation_data_create()
    action = bpy.data.actions.new('Sword_UppercutV12_'+variant)
    action.use_fake_user = True
    rig.animation_data.action = action
    result,previous,blend_previous = [],{},{}
    for i in range(FRAMES+1):
        t = source_time(i)
        rows = sample_keys(accepted['samples'],t)
        base = {n:canonical(m) for n,m in globalize({n:native(k) for n,k in rows.items()}).items()}
        pose = {n:m.copy() for n,m in base.items()}
        low_weight = smooth(i/32) if i<=32 else (1. if i<=96 else 1.-smooth((i-96)/9))
        high_weight = smooth((i-96)/15) if i<=111 else (1. if i<=120 else 1.-smooth((i-120)/78))
        lift = Vector((-.025,.055,.20))*high_weight
        if high_weight>0.:
            carry = Matrix.Translation(lift)
            for n in WEAPON|HANDS['l']|HANDS['r']:pose[n] = carry@base[n]
            for side in ('l','r'):raise_supported_arm(pose,base,side)
        group = Matrix.Translation(offscreen*low_weight)
        pose = {n:group@m for n,m in pose.items()}
        ue = {n:mat(C@m.translation*100,(C@m.to_quaternion().to_matrix()@C).to_quaternion(),m.to_scale()) for n,m in pose.items()}
        keys = {}
        for n,m in localize(ue).items():
            p,q,s = m.decompose()
            if n in previous and q.dot(previous[n])<0:q = -q
            keys[n] = dict(p=list(p),q=list(q),s=list(s))
            # Finger articulation stays exactly on the V11 idle-derived keys.
            if n in (HANDS['l']-{'hand_l'})|(HANDS['r']-{'hand_r'}):keys[n] = rows[n]
            previous[n] = Quaternion(keys[n]['q'])
        if i in (0,FRAMES):keys = rows
        result.append(dict(seconds=i/FPS,source_seconds=t,bones=keys))
        scene.frame_set(i)
        apply_blender(pose)
        for bone in rig.pose.bones:
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
    patch = dict(revision='OffscreenRiseUppercutV12',variant=variant,source_keys=str(source),
                 fps=FPS,intervals=FRAMES,seconds=FRAMES/FPS,release_seconds=.8,
                 main_stroke_seconds=9/FPS,offscreen_translation_m=list(offscreen),
                 extra_lift_m=[-.025,.055,.20],samples=result)
    (out/'editable_keys.json').write_text(json.dumps(patch,separators=(',',':')),encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'Sword_UppercutV12_Editable.blend'))
    receipts[variant] = dict(seconds=FRAMES/FPS,offscreen_translation_m=list(offscreen),
        author_surface_bottom_envelope_m=highest,keys=str(out/'editable_keys.json'),
        blend=str(out/'Sword_UppercutV12_Editable.blend'))
    print('UPPERCUT_V12_AUTHORED '+variant+' '+json.dumps(receipts[variant]),flush=True)
(P/'authoring.json').write_text(json.dumps(dict(revision='OffscreenRiseUppercutV12',
    fps=FPS,seconds=FRAMES/FPS,release_seconds=.8,main_stroke_seconds=.075,
    main_stroke_end=.875,follow_end=.925,settle_end=1.,extra_lift_m=.20,
    method='V11 idle-derived grips; entire-rig windup translation; higher fixed-grip two-bone rise with transported elbow planes',
    variants=receipts,paid_motion_used=False,runtime_tested=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf-8')
