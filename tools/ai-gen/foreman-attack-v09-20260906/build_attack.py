"""Attack-only revision on the existing V08 skinned mesh. Blender 5.1."""
import ast
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

R = Path(__file__).resolve().parent
SOURCE = R.parent / 'foreman-retopo-v08-20260906/foreman-retopo-v08.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
s = bpy.context.scene
a = bpy.data.objects['ForemanRig']
body = bpy.data.objects['ForemanBody']
whip = bpy.data.objects['Whip']
FPS = 80
s.render.fps = FPS
for track in a.animation_data.nla_tracks:
    track.mute = True
rest = {b.name: b.matrix_local.copy() for b in a.data.bones}
defs = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in a.data.bones}
lengths = {n: (t-h).length for n, (h,t) in defs.items()}
# Reuse just the established mathematical helpers, not the V07 build pipeline.
upstream = R.parent / 'foreman-downstroke-v07-20260906/build_motion.py'
tree = ast.parse(upstream.read_text(encoding='utf-8'))
helpers = {'curve', 'vk', 'rot', 'matrix', 'limb_matrix', 'two'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in helpers], type_ignores=[]), str(upstream), 'exec'))

old = bpy.data.actions['Attack']
a.animation_data.action = old
if old.slots:
    a.animation_data.action_slot = old.slots[0]
s.frame_set(0)
endpoint = {b.name: b.matrix_basis.copy() for b in a.pose.bones}
s.frame_set(120)
end_pose = {b.name: b.matrix_basis.copy() for b in a.pose.bones}
a.animation_data.action = None
bpy.data.actions.remove(old)
act = bpy.data.actions.new('Attack')
act.use_fake_user = True
a.animation_data.action = act

# Pitch/yaw/drop: broad anticipation, fast transfer, small continued follow-through.
torso = vk([(0,(.07,0,.02)),(.16,(-.025,-.16,.045)),(.33,(-.14,-.48,.055)),
    (.405,(-.10,-.46,.06)),(.48,(.28,-.03,.14)),(.56,(.64,.43,.22)),
    (.625,(.72,.54,.245)),(.75,(.61,.47,.215)),(.94,(.38,.29,.145)),
    (1.18,(.16,.08,.06)),(1.5,(.07,0,.02))])
right = vk([(0,(-.20,-.12,-.65)),(.13,(-.32,.075,-.43)),(.25,(-.25,.23,.15)),
    (.355,(-.08,.10,.51)),(.405,(-.065,-.09,.53)),(.45,(-.28,-.19,.37)),
    (.495,(-.38,-.27,.02)),(.55,(-.29,-.24,-.46)),(.59,(-.18,-.20,-.65)),
    (.68,(-.14,-.16,-.70)),(.83,(-.17,-.13,-.65)),(1.06,(-.24,-.08,-.60)),
    (1.27,(-.23,-.11,-.63)),(1.5,(-.20,-.12,-.65))])
left = vk([(0,(.22,-.12,-.64)),(.18,(.33,-.22,-.43)),(.34,(.42,-.31,-.25)),
    (.44,(.34,-.30,-.27)),(.55,(.18,-.13,-.37)),(.65,(.15,.04,-.46)),
    (.80,(.23,.11,-.54)),(1.04,(.30,-.01,-.55)),(1.28,(.25,-.12,-.61)),
    (1.5,(.22,-.12,-.64))])

def ss(t, start, end):
    u = max(0., min(1., (t-start)/(end-start)))
    return u*u*(3-2*u)

def whip_pose(grip, direction, t, floor):
    points = []
    for i in range(129):
        u = i/128
        angle = u*math.tau*2.10
        coil = Vector((.39*math.sin(angle)*(1-.15*u), -.13*u-.11*math.sin(math.pi*u), -.46*(1-math.cos(angle))-.05*u))
        over = Vector((-.22*math.sin(math.pi*u),4.8*u,1.1*math.sin(math.pi*u)))
        crest = Vector((-.14*math.sin(math.pi*u),-2.6*u,3.5*math.sin(math.pi*u*.72)))
        contact = Vector((.06*math.sin(math.tau*u),-6.1*u,-.70*u))
        follow = Vector((.48*math.sin(math.pi*u),-5.2*u,-1.5*u))
        recoil = Vector((.85*math.sin(math.pi*u),-3.0*u,-.9*u))
        # The distal contact key arrives at .53125 + .065 = .59625 s.
        local_t = t-.065*u
        offset = curve(local_t,[(0,coil),(.35,over),(.43,crest),(.53125,contact),
            (.64,follow),(.87,recoil),(1.355,coil),(1.5,coil)])
        if .62<t<1.42:
            envelope = math.sin(math.pi*(t-.62)/.80)**2
            offset += Vector((.24*math.sin(13*(t-.62)-6*u),.09*math.sin(12*(t-.62)-6*u),.16*math.sin(14*(t-.62)-6*u)))*u*envelope
        # Respect the grip direction near the handle; smoothly join the free curve.
        join = ss(u,0,.075)
        offset = (direction*(6.4*u)).lerp(offset,join)
        points.append(grip+offset)
    # Keep the approved length and ground floor without scaling any deform bone.
    for _ in range(16):
        length = sum((q-p).length for p,q in zip(points,points[1:]))
        scale = 6.4/max(.001,length)
        points = [grip+(p-grip)*scale for p in points]
        for p in points:
            p.z = max(floor,p.z)
    distance = [0.]
    for p,q in zip(points,points[1:]):
        distance.append(distance[-1]+(q-p).length)
    rings = []
    cursor = 0
    for i in range(33):
        target = distance[-1]*i/32
        while cursor<127 and distance[cursor+1]<target:
            cursor += 1
        f = (target-distance[cursor])/max(1e-8,distance[cursor+1]-distance[cursor])
        rings.append(points[cursor].lerp(points[cursor+1],f))
    normal = Vector((0,1,0))
    for i,p in enumerate(rings):
        tangent = (rings[min(32,i+1)]-rings[max(0,i-1)]).normalized()
        normal -= tangent*normal.dot(tangent)
        if normal.length<1e-5:
            normal = Vector((1,0,0))-tangent*tangent.x
        normal.normalize()
        m = Matrix((normal,tangent,normal.cross(tangent))).transposed().to_4x4()
        m.translation = p
        a.pose.bones[f'whip.{i:02d}'].matrix = m

def pose(t):
    for pb in a.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    lean,twist,drop = curve(t,torso)
    shift = curve(t,[(0,0),(.32,.055),(.43,.025),(.58,-.10),(.70,-.12),(.96,-.065),(1.5,0)])
    sway = curve(t,[(0,0),(.31,-.045),(.49,.005),(.65,.045),(.92,.02),(1.5,0)])
    head = Vector((sway,.06+shift,1.23-drop))
    mats = {}
    for i,n in enumerate(['pelvis','spine','chest','neck','head']):
        delayed = curve(t-[0,.018,.033,.050,.067][i],torso)
        basis = rot(delayed.x*[.38,.76,1,.77,.62][i], delayed.y*[.56,.82,1,.78,.67][i], -sway*[.2,.45,.65,.3,.2][i])
        m = mats[n] = matrix(n,head,basis@Vector((0,0,lengths[n])),basis)
        head = m.translation+m.to_3x3()@Vector((0,lengths[n],0))
    cd = mats['chest']@rest['chest'].inverted()
    pd = mats['pelvis']@rest['pelvis'].inverted()
    cb = cd.to_3x3().normalized()
    for side,sign in [('L',1),('R',-1)]:
        cl,ua,fa,ha = [n+'.'+side for n in ['clavicle','upper_arm','forearm','hand']]
        shoulder = cd@defs[cl][1]
        shoulder.z += curve(t,[(0,0),(.35,.040 if side=='R' else .018),(.62,.010),(1.5,0)])
        clavicle = cd@defs[cl][0]
        matrix(cl,clavicle,shoulder-clavicle,cb)
        target = shoulder+cb@curve(t,left if side=='L' else right)
        pole = cb@Vector((sign*.35,.90,.05))
        elbow,wrist = two(shoulder,target,lengths[ua],lengths[fa],pole)
        plane = (elbow-shoulder).cross(wrist-elbow).normalized()
        rest_plane = (defs[ua][1]-defs[ua][0]).cross(defs[fa][1]-defs[fa][0]).normalized()
        limb_matrix(ua,shoulder,elbow-shoulder,plane,rest_plane)
        fm = limb_matrix(fa,elbow,wrist-elbow,plane,rest_plane)
        fb = (fm@rest[fa].inverted()).to_3x3().normalized()
        flex = curve(t-(.025 if side=='R' else .040),[(0,.1),(.36,-.15),(.46,-.27),(.575,.44),(.66,.36),(.86,.18),(1.5,.1)])
        hdir = (fb@Matrix.Rotation(flex,3,'X')@rest[fa].to_3x3()@Vector((0,1,0))).normalized()
        hm = matrix(ha,wrist,hdir,fb)
        delta = hm@rest[ha].inverted()
        curl = .88 if side=='R' else curve(t,[(0,.19),(.34,.05),(.62,.48),(.85,.28),(1.5,.19)])
        for part,amount in [('fingers_cup',curl),('fingers_tip',curl*.60),('thumb',.85 if side=='R' else .15)]:
            pb = a.pose.bones[part+'.'+side]
            axis = Vector((.8,-sign*.5,0)).normalized() if part=='thumb' else Vector((0,sign,0))
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = Quaternion(rest[pb.name].to_3x3().inverted()@axis,amount)
        if side=='R':
            grip = delta@Vector((-.805,-.235,1.18))
            grip_dir = (delta.to_3x3()@Vector((0,-1,0))).normalized()
        th,sn,fo = [n+'.'+side for n in ['thigh','shin','foot']]
        hip = pd@defs[th][0]
        ankle = defs[sn][1].copy()
        if side=='L':
            step = .40*ss(t,.24,.50)*(1-ss(t,.98,1.36))
            ankle.y -= step
            if .24<t<.50:
                ankle.z += .075*math.sin(math.pi*(t-.24)/.26)**2
            if .98<t<1.36:
                ankle.z += .060*math.sin(math.pi*(t-.98)/.38)**2
        knee,ankle = two(hip,ankle,lengths[th],lengths[sn],Vector((sign*.08,-1,.05)))
        matrix(th,hip,knee-hip)
        matrix(sn,knee,ankle-knee)
        matrix(fo,ankle,defs[fo][1]-defs[fo][0])
    bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    low = min((ev.matrix_world@v.co).z for v in mesh.vertices)
    ev.to_mesh_clear()
    whip_pose(grip,grip_dir,t,.020+low)
    root = a.pose.bones['root']
    m = root.matrix.copy()
    m.translation.z += .005-low
    root.matrix = m
    # Match the established idle boundary exactly; the central attack is unblended.
    blend = ss(t,0,.10)*(1-ss(t,1.37,1.5))
    if blend<1:
        for pb in a.pose.bones:
            boundary = endpoint[pb.name] if t<.10 else end_pose[pb.name]
            pb.matrix_basis = boundary.lerp(pb.matrix_basis,blend)
    bpy.context.view_layer.update()
    return .005-low

previous = {}
corrections = []
for t in sorted(set([i/FPS for i in range(121)]+[.59625])):
    corrections.append(pose(t))
    for pb in a.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        if pb.name in previous and pb.rotation_quaternion.dot(previous[pb.name])<0:
            pb.rotation_quaternion.negate()
        previous[pb.name] = pb.rotation_quaternion.copy()
        for channel in ['location','rotation_quaternion','scale']:
            pb.keyframe_insert(channel,frame=t*FPS,group=pb.name)
for slot in act.slots:
    for layer in act.layers:
        for strip in layer.strips:
            bag = strip.channelbag(slot)
            if bag:
                for fc in bag.fcurves:
                    for key in fc.keyframe_points:
                        key.interpolation = 'LINEAR'
# Pack the existing images so the new source is independent of relative texture paths.
for im in bpy.data.images:
    if im.source=='FILE' and not im.packed_file:
        im.filepath = bpy.path.abspath(im.filepath)
        im.pack()
a.animation_data.action = bpy.data.actions['Idle']
s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'foreman-attack-v09.blend'))
bpy.ops.object.select_all(action='DESELECT')
for obj in [a,body,whip,bpy.data.objects['WhipHandle']]:
    obj.select_set(True)
bpy.context.view_layer.objects.active = a
bpy.ops.export_scene.gltf(filepath=str(R/'foreman-attack-v09.glb'),export_format='GLB',use_selection=True,
    export_animations=True,export_animation_mode='ACTIONS',export_frame_range=False,
    export_force_sampling=True,export_frame_step=1,export_def_bones=True)
report = {'source':str(SOURCE),'attack_seconds':1.5,'contact_seconds':.59625,'source_fps':FPS,
    'authored_samples':122,'bone_count':len(rest),'ground_correction_m':[min(corrections),max(corrections)],
    'modified_actions':['Attack'],'mesh_and_weights_modified':False,'phase_delay_to_tip_s':.065}
(R/'build-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('FOREMAN_V09_BUILD_COMPLETE',json.dumps(report))
