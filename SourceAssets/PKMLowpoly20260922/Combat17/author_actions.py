"""PKM fitted tactical sprint and stock bash. Author/export only; no tests/render."""
import ast
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

O = Path(__file__).parent
R = O.parent
S = R.parent
FPS = 120
bpy.context.preferences.filepaths.save_version = 0

def smooth(x):
    x = max(0., min(1., x))
    return x*x*(3-2*x)

def ramp(t, a, b):
    return smooth((t-a)/(b-a))

def mix(a, b, w):
    p, q, s = a.decompose(); p1, q1, s1 = b.decompose()
    return Matrix.LocRotScale(p.lerp(p1, w), q.slerp(q1, w), s.lerp(s1, w))

def frame(axis, width):
    x = axis.normalized(); y = width-x*width.dot(x)
    if y.length < 1e-7: y = x.orthogonal()
    y.normalize()
    return Matrix((x, y, x.cross(y).normalized())).transposed()

def action(rig, clip):
    rig.animation_data.action = clip
    rig.animation_data.action_slot = clip.slots[0]

def sample(rig, clip, f):
    action(rig, clip)
    bpy.context.scene.frame_set(int(f), subframe=f % 1)
    bpy.context.view_layer.update()
    return {b.name: b.matrix.copy() for b in rig.pose.bones}

# Reuse the current PKM rest-frame arm solver without executing its reload author.
tree = ast.parse((R/'Reload16/author_reload.py').read_text(encoding='utf-8'))
solver = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'solve_arm')
exec(compile(ast.Module(body=[solver], type_ignores=[]), '<PKM Reload16 arm support>', 'exec'))

# Current grip-locked QBZ motion supplies only the weapon path and event rhythm.
donor_file = S/'QBZ191QuickMeleeGrip20260919O/Base/QBZ191_QuickCombat_Base_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(donor_file), use_scripts=False)
dr = bpy.data.objects['SK_M4_Infima']
da = bpy.data.actions['QBZ191_QuickCombat_O_Base']
donor = [sample(dr, da, f)['WPN_root'] for f in range(109)]
donor_stock = Vector((.00072809, .20850360, .05925570))
# This is the actual PKM anchor already used by the game's contact query.
pkm_stock = Vector((-.00003818, .359063, -.027))
record = {}
details = {'fps': FPS, 'melee_source': str(donor_file), 'melee_contact_seconds': 1/6,
           'sprint_reference': 'ASH12TacticalSprint20260919/author_sprint.py; existing M4 grip transitions',
           'sprint_elevation_degrees': 76, 'pkm_stock_root_m': list(pkm_stock),
           'idle_sources': {}, 'runtime_tested': False}

for family in ['base', 'vertical', 'canted', 'prism', 'angled']:
    source = R/'Feed13/PKM_FiringFeed_Editable.blend' if family == 'base' else R/'GripContact15'/f'PKM_{family}_Editable.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
    r = bpy.data.objects['PKM_Manny_Rig']; scene = bpy.context.scene
    r.data.pose_position = 'POSE'
    idle_name = 'PKM_Game_idle_Wrist12' if family == 'base' else f'A_PKM_{family}_idle_Contact15'
    idle = sample(r, bpy.data.actions[idle_name], 0)
    rest = {b.name: b.matrix_local.copy() for b in r.data.bones}
    parents = {b.name: b.parent.name if b.parent else None for b in r.data.bones}
    localrest = {n: rest[parents[n]].inverted()@m if parents[n] else m.copy() for n, m in rest.items()}
    names = list(rest)
    weapon = {'WPN_root'} | {b.name for b in r.data.bones['WPN_root'].children_recursive}
    weapon |= {n for n in names if n.startswith(('WPN_', 'PKM_', 'New_PKM_'))}
    hands = {side: {'hand_'+side} | {b.name for b in r.data.bones['hand_'+side].children_recursive} for side in ['l', 'r']}
    fingers = {side: [n for n in names if n.endswith('_'+side) and n.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_'))] for side in ['l', 'r']}
    details['idle_sources'][family] = {'file': str(source), 'action': idle_name}
    W0 = idle['WPN_root']; up = Vector((0, 0, 1))
    barrel = (idle['WPN_SOCKET_Muzzle'].translation-W0.translation).normalized()
    forward = Vector((barrel.x, barrel.y, 0)).normalized()
    right = forward.cross(up).normalized()
    upright = forward*math.cos(math.radians(76))+up*math.sin(math.radians(76))
    raise_rotation = Quaternion(up, math.radians(-7)) @ Quaternion(upright, math.radians(-8)) @ barrel.rotation_difference(upright)
    wrist_idle = idle['lowerarm_l'].to_quaternion().inverted() @ idle['hand_l'].to_quaternion()
    wrist_rest = rest['lowerarm_l'].to_quaternion().inverted() @ rest['hand_l'].to_quaternion()

    def arm(pose, side, target, weight):
        # Solve against the unchanged fitted idle; transport the whole hand.
        fitted = solve_arm(idle, side, target, weight)
        for n in names:
            if n.endswith('_'+side) and n.startswith(('clavicle_', 'upperarm_', 'lowerarm_')):
                pose[n] = fitted[n]
        delta = target @ idle['hand_'+side].inverted()
        for n in hands[side]: pose[n] = delta @ idle[n]
        ik = 'ik_hand_'+side
        if ik in pose: pose[ik] = target.copy()

    def sprint(progress, phase=None):
        pose = {n: m.copy() for n, m in idle.items()}
        if progress <= 0: return pose
        released = ramp(progress, 0, .22)
        withdrawn = ramp(progress, .10, .65)
        raised = ramp(progress, .25, 1.)
        sway = math.sin(phase) if phase is not None else 0.
        step = math.sin(2*phase) if phase is not None else 0.
        # Keep the heavier receiver/box beside the view and the muzzle up.
        offset = (right*.125 + forward*.060 - up*.025)*raised
        offset += (right*(.004*sway)+forward*(.005*step)-up*(.004*step))*raised
        stride = Quaternion(right, math.radians(.85*sway)) @ Quaternion(up, math.radians(.5*step))
        q = Quaternion().slerp(stride@raise_rotation, raised)
        pivot = idle['hand_r'].translation
        delta = Matrix.Translation(pivot+offset) @ q.to_matrix().to_4x4() @ Matrix.Translation(-pivot)
        for n in weapon: pose[n] = delta@idle[n]
        arm(pose, 'r', delta@idle['hand_r'], raised)

        # The support hand clears the grip before the gun begins to rise.
        shoulder = idle['upperarm_l'].translation
        clear = idle['hand_l'].translation + (-right*.05-forward*.005-up*.055)*released
        l1 = (idle['lowerarm_l'].translation-shoulder).length
        l2 = (idle['hand_l'].translation-idle['lowerarm_l'].translation).length
        dx, dy = -.055-.004*sway, .015+.024*sway
        reach = .955*(l1+l2)
        target = shoulder+right*dx+forward*dy-up*math.sqrt(reach*reach-dx*dx-dy*dy)
        v0, v1 = clear-shoulder, target-shoulder
        d0, d1 = v0.normalized(), v1.normalized(); axis = d0.cross(d1)
        direction = d0.lerp(d1, withdrawn).normalized() if axis.length < 1e-6 else Quaternion(axis.normalized(), d0.angle(d1)*withdrawn)@d0
        direction = (direction-right*(.30*math.sin(math.pi*withdrawn))).normalized()
        location = shoulder+direction*(v0.length+(v1.length-v0.length)*(1-(1-withdrawn)**4))
        hand = idle['hand_l'].copy(); hand.translation = location
        # Transport the forearm frame first, then relax the wrist relative to it.
        initial = solve_arm(idle, 'l', hand, released)
        relaxed = wrist_idle.slerp(wrist_rest, min(1., .55*released+.40*withdrawn))
        hand = Matrix.LocRotScale(location, initial['lowerarm_l'].to_quaternion()@relaxed, hand.to_scale())
        arm(pose, 'l', hand, released)
        for n in fingers['l']:
            if '_metacarpal_' in n: continue
            p = parents[n]; local = idle[p].inverted()@idle[n]
            pose[n] = pose[p]@mix(local, localrest[n], .60*released)
        return pose

    def melee(index):
        pose = {n: m.copy() for n, m in idle.items()}
        if index == 0 or index == 108: return pose
        t = index/FPS
        weight = ramp(t, 0, .10)*(1-ramp(t, .72, .90))
        alignment = W0@donor[0].inverted()
        W = alignment@donor[index]
        # Preserve the donor's stock displacement, measured from PKM's own stock.
        travel = alignment.to_3x3()@((donor[index]@donor_stock)-(donor[0]@donor_stock))
        desired = W0@pkm_stock+travel
        W.translation = desired-W.to_3x3()@pkm_stock
        delta = W@W0.inverted()
        # Move the rigid weapon/hand group into both arms' reach; don't stretch arms.
        correction = Vector(); residual = [Vector(), Vector()]
        for _ in range(24):
            for j, side in enumerate(['r', 'l']):
                sh = idle['upperarm_'+side].translation
                el = idle['lowerarm_'+side].translation
                wr = idle['hand_'+side].translation
                maxreach = max((wr-sh).length, .955*((el-sh).length+(wr-el).length))
                center = sh-(delta@idle['hand_'+side]).translation
                trial = correction+residual[j]; v = trial-center
                result = center+v.normalized()*maxreach if v.length > maxreach else trial
                residual[j] = trial-result; correction = result
        delta.translation += correction
        for n in weapon: pose[n] = delta@idle[n]
        for side in ['r', 'l']: arm(pose, side, delta@idle['hand_'+side], weight)
        return pose

    def bake(kind, poses):
        duration = (len(poses)-1)/FPS
        a = bpy.data.actions.new(f'PKM17_{family}_{kind}'); a.use_fake_user = True
        r.animation_data.action = a
        for b in r.pose.bones:
            b.rotation_mode = 'QUATERNION'
            for prop in ['location', 'rotation_quaternion', 'scale']: b.keyframe_insert(prop, frame=0)
        curves = {(c.data_path, c.array_index): c for layer in a.layers for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves}
        for n in names:
            values = []; prev = None
            for p in poses:
                basis = localrest[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n])
                loc, q, scale = basis.decompose()
                if prev is not None and prev.dot(q) < 0: q.negate()
                prev = q.copy(); values.append((loc, q, scale))
            for prop, field, count in [('location', 0, 3), ('rotation_quaternion', 1, 4), ('scale', 2, 3)]:
                for axis in range(count):
                    c = curves[(f'pose.bones["{n}"].{prop}', axis)]
                    c.keyframe_points.clear(); c.keyframe_points.add(len(values))
                    c.keyframe_points.foreach_set('co', [v for i, row in enumerate(values) for v in (i, row[field][axis])])
                    for key in c.keyframe_points: key.interpolation = 'LINEAR'
                    c.update()
        action(r, a); scene.render.fps = FPS; scene.render.fps_base = 1
        scene.frame_start = 0; scene.frame_end = len(poses)-1; scene.frame_set(0)
        bpy.ops.object.select_all(action='DESELECT'); r.hide_set(False); r.select_set(True); bpy.context.view_layer.objects.active = r
        name = 'A_PKM_'+('' if family == 'base' else family+'_')+kind
        dest = O/'Animations'/family; dest.mkdir(parents=True, exist_ok=True)
        bpy.ops.export_scene.fbx(filepath=str(dest/(name+'.fbx')), use_selection=True, object_types={'ARMATURE'}, axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True, bake_anim_step=1, bake_anim_simplify_factor=0)
        record[family+'/'+kind] = {'name': name, 'action': a.name, 'seconds': duration, 'fps': FPS}
        (O/'animations.json').write_text(json.dumps(record, indent=2))
        print('PKM17_EXPORTED', family, kind, flush=True)

    entry = [sprint(i/42) for i in range(43)]
    bake('sprint_enter', entry)
    bake('sprint_loop', [sprint(1., 2*math.pi*i/72) for i in range(73)])
    bake('sprint_exit', list(reversed(entry)))
    bake('quick_melee', [melee(i) for i in range(109)])
    action(r, bpy.data.actions[f'PKM17_{family}_sprint_enter'])
    scene.frame_start = 0; scene.frame_end = 42; scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=str(O/f'PKM_{family}_Combat_Editable.blend'))
    (O/'authoring.json').write_text(json.dumps(details, indent=2))
print('PKM17_AUTHOR_COMPLETE', flush=True)
