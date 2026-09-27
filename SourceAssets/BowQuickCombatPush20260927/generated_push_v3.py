"""Author the V7 bow's grab / down-left sweep / release, without rendering.

The V11 source supplies the native binding and accepted left grasp. Mirror that
complete grasp into the right-hand anatomy, then transport both contacts with
the bow. Arm bones retain their lengths; fingers close before acceleration.
"""
import bpy, json, math, re
from pathlib import Path
from mathutils import Matrix, Vector

P = Path(__file__).parent
PROJECT = P.parents[1]
BASE = PROJECT / 'SourceAssets/BowSightContact20260926'
source = (BASE / 'generated_actions.py').read_text(encoding='utf-8')
ns = {'__file__': str(BASE / 'generated_actions.py')}
exec(compile(source.split('bpy.ops.wm.read_factory_settings(use_empty=True)')[0],
             str(BASE / 'generated_actions.py'), 'exec'), ns)
for key in ('rest', 'local', 'parent', 'order', 'mat', 'smooth', 'hand_path',
            'blend_frame', 'world_to_blender', 'limb_frame', 'anatomy', 'R'):
    globals()[key] = ns[key]
timing_source = (PROJECT / 'Source/FPSGAME/Weapons/Bow/BowQuickCombatMotion.h').read_text()
timing = {k: float(re.search(r'constexpr float '+k+r' = ([.\d]+)f;', timing_source)[1])
          for k in ('Length', 'Grip', 'Cock', 'Contact', 'Follow', 'LetGo')}
L, G, C, HIT, F, RELEASE = (timing[k] for k in ('Length','Grip','Cock','Contact','Follow','LetGo'))
FPS = 240
OUT = P / 'Export'; OUT.mkdir(parents=True, exist_ok=True)
idle = ns['pose']('Idle', 0.)
idle_bow = idle['bow_grip']
left_contact = idle_bow.inverted() @ idle['hand_l']

# Reflect the accepted closed left hand across the bow's grip plane. Account
# for the opposite native bind frame, rather than copying left Euler angles.
# Right palm wraps 30 cm above the left; transport the whole grasp onto the curved upper riser.
mirror = Matrix.Diagonal((1., -1., 1., 1.))
grip_mirror = Matrix.Translation((-3.896789312362671, 0.24576873397827148, 30.0)) @ mirror
right_grasp = {}
for n in order:
    other = n[:-2]+'_l' if n.endswith('_r') else ''
    if n == 'hand_r' or (other in idle and n.split('_')[0] in ('index','middle','ring','pinky','thumb')):
        right_grasp[n] = grip_mirror @ idle_bow.inverted() @ idle[other] @ rest[other].inverted() @ mirror @ rest[n]
right_contact = right_grasp['hand_r']
right_closed_local = {n: right_grasp[parent[n]].inverted() @ m for n,m in right_grasp.items()
                      if n != 'hand_r' and parent[n] in right_grasp}
idle_local = {n: idle[parent[n]].inverted() @ idle[n] if parent[n] else idle[n] for n in order}
left_closed_local = {n: idle_local[n] for n in order
                     if n.endswith('_l') and n.split('_')[0] in ('index','middle','ring','pinky','thumb')}

# Small lift during the reach, visible right/up loading, fast diagonal sweep,
# then deceleration before the returning hand releases. Contact is an interior
# Hermite waypoint, so the bow does not stop at the hit frame.
# Centre the two separated grips after the live +32 cm hip offset.
# Turn to exactly horizontal before accelerating, then preserve that plane.
keys = [
    (0., (46.,-20.,-20.), (0.,0.,-30.)),
    (G,  (48.,-44.,-9.),  (0.,0.,-42.)),
    (C,  (43.,-47.,-3.),  (0.,0.,-90.)),
    (HIT,(61.,-47.,-3.),  (0.,0.,-90.)),
    (F,  (63.,-47.,-3.),  (0.,0.,-90.)),
    (RELEASE,(47.,-42.,-8.),(0.,0.,-64.)),
    (L,  (46.,-20.,-20.), (0.,0.,-30.)),
]
def bow_at(t):
    p = hand_path([(a,Vector(p)) for a,p,r in keys],t)
    angles = Vector(keys[-1][2])
    for (a,_,ra),(b,_,rb) in zip(keys,keys[1:]):
        if a <= t <= b:
            angles = Vector(ra).lerp(Vector(rb),smooth((t-a)/(b-a)))
            break
    # Zero angular velocity at the ends of the turn; exact -90 degrees throughout the push.
    r = Matrix.Rotation(math.radians(angles.y),3,'Z') @ Matrix.Rotation(math.radians(angles.x),3,'Y') @ Matrix.Rotation(math.radians(angles.z),3,'X')
    return mat(p,r)

def pose(t):
    bow = bow_at(t)
    load = smooth(t/G)*(1.-smooth((t-RELEASE)/(L-RELEASE)))
    left = bow @ left_contact
    right = bow @ right_contact
    if t < G:
        # The wrist approaches from camera-right, with room for open fingers;
        # the last four centimetres seat the palm before the swing starts.
        target = right.translation
        p = hand_path([(0.,idle['hand_r'].translation),(.065,target+Vector((-5.,14.,6.))),
                       (.11,target+Vector((0.,4.,2.))),(G,target)],t)
        right = mat(p,idle['hand_r'].to_quaternion().slerp(right.to_quaternion(),smooth(t/.125)).to_matrix())
    elif t > RELEASE:
        u = smooth((t-RELEASE)/(L-RELEASE))
        peel = math.sin(math.pi*u)
        right = blend_frame(right,idle['hand_r'],u)
        right.translation += Vector((-2.,8.,-3.))*peel
    closed = smooth((t-.105)/(G-.105))*(1.-smooth((t-RELEASE)/.095))
    targets = {'l':left,'r':right}
    w = {n:m.copy() for n,m in idle.items()}
    # Centre the shoulder girdle under the horizontal two-handed grip. Elbows
    # follow the forward drive while the native limb lengths remain fixed.
    drive = bow.translation-idle_bow.translation
    for side in ('l','r'):
        clav,up,low,hand = ('clavicle_'+side,'upperarm_'+side,'lowerarm_'+side,'hand_'+side)
        shoulder = idle[up].translation + drive*.22
        shoulder += Vector((3., (2. if side=='r' else 0.)-20., 1.))*load
        target = targets[side]
        wrist = target.translation
        l1 = local[low].translation.length
        l2 = local[hand].translation.length
        axis = (wrist-shoulder).normalized()
        distance = (wrist-shoulder).length
        # Smoothly recruit the shoulder girdle before either elbow locks.
        reach = (l1+l2)*.96
        if distance > reach:
            shoulder += axis*(distance-reach)
            distance = reach
        pole = idle[low].translation + drive*.35
        pole += Vector((-1., (8. if side=='r' else -4.)-14., -5.))*load
        bend = (pole-shoulder)-axis*(pole-shoulder).dot(axis)
        bend.normalize()
        a = (l1*l1-l2*l2+distance*distance)/(2*distance)
        elbow = shoulder + axis*a + bend*math.sqrt(max(0.,l1*l1-a*a))
        hand_delta = target.to_3x3() @ rest[hand].to_3x3().transposed()
        ru = rest[low].translation-rest[up].translation
        rl = rest[hand].translation-rest[low].translation
        ud,ld = (elbow-shoulder).normalized(),(wrist-elbow).normalized()
        across = R @ Vector(anatomy[side]['across'])
        dl = limb_frame(ld,hand_delta@across) @ limb_frame(rl,across).transposed()
        du = limb_frame(ud,ud.cross(ld)) @ limb_frame(ru,ru.cross(rl)).transposed()
        compatible = limb_frame(ud,hand_delta@across) @ limb_frame(ru,across).transposed()
        twist_share = .25 if side=='l' else .25*load
        du = du.to_quaternion().slerp(compatible.to_quaternion(),twist_share).to_matrix()
        w[clav].translation = shoulder-w[clav].to_3x3()@local[up].translation
        w[up],w[low],w[hand] = mat(shoulder,du@rest[up].to_3x3()),mat(elbow,dl@rest[low].to_3x3()),target
        descendants = {up,low,hand}
        for n in order:
            if parent[n] in descendants and n not in (low,hand):
                descendants.add(n)
                value = local[n].copy()
                if n in left_closed_local:
                    value = left_closed_local[n].copy()
                elif n.endswith('_r') and n.split('_')[0] in ('index','middle','ring','pinky','thumb'):
                    value = idle_local[n].copy()
                    if n in right_closed_local:
                        # Native translations retain every phalange's length.
                        value = mat(value.translation, value.to_quaternion().slerp(
                            right_closed_local[n].to_quaternion(),closed).to_matrix())
                w[n] = w[parent[n]] @ value
    w['bow_grip'] = bow
    w['bow_nock'] = bow @ mat(ns['BRACE'])
    # Same exact resting pose at both ends, with a short local-space handoff
    # at the ends so the V11 shoulder frame is inherited without a pop.
    edge = smooth(t/.045)*(1.-smooth((t-(L-.075))/.075))
    if edge < 1.:
        sampled = {n:m.copy() for n,m in w.items()}
        for n in order:
            current = sampled[parent[n]].inverted()@sampled[n] if parent[n] else sampled[n]
            relative = blend_frame(idle_local[n],current,edge)
            w[n] = w[parent[n]]@relative if parent[n] else relative
    return w

bpy.ops.wm.open_mainfile(filepath=str(BASE/'Bow_SupportClearanceV11.blend'))
bpy.context.preferences.filepaths.save_version = 0
rig = bpy.data.objects['Bow_V7_Native']; arm = rig.data
scene = bpy.context.scene; scene.render.fps = FPS
rig.animation_data_create()
action = bpy.data.actions.new('A_Bow_QuickCombat'); rig.animation_data.action = action
scene.frame_start=0; scene.frame_end=round(L*FPS)
previous={}
for frame in range(scene.frame_end+1):
    world = pose(frame/FPS)
    for n in order:
        b=rig.pose.bones[n]
        relative=world_to_blender(world[parent[n]]).inverted()@world_to_blender(world[n]) if parent[n] else world_to_blender(world[n])
        restlocal=arm.bones[parent[n]].matrix_local.inverted()@arm.bones[n].matrix_local if parent[n] else arm.bones[n].matrix_local
        b.rotation_mode='QUATERNION'; b.matrix_basis=restlocal.inverted()@relative
        if frame and b.rotation_quaternion.dot(previous[n])<0: b.rotation_quaternion.negate()
        previous[n]=b.rotation_quaternion.copy()
        b.keyframe_insert('location',frame=frame); b.keyframe_insert('rotation_quaternion',frame=frame); b.keyframe_insert('scale',frame=frame)
scene.frame_set(0); bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'A_Bow_QuickCombat.fbx'),use_selection=True,
    object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_QuickCombat.blend'))
(P/'authoring.json').write_text(json.dumps({'fps':FPS,'timing_seconds':timing,
    'asset':'/Game/Weapons/DarkBow20260925/QuickCombat20260926/A_Bow_QuickCombat',
    'source_binding':'ContactV9 / V7 native bow arms / V11 idle',
    'right_grasp':'Complete left closed grasp mirrored into opposite native anatomy; 30 cm above left grip; fitted to real upper-limb centreline; horizontal forward push',
    'bow_keys':keys,'runtime_tested':False},indent=2),encoding='utf-8')
print('BOW_HORIZONTAL_PUSH_AUTHORED',str(OUT/'A_Bow_QuickCombat.fbx'))
