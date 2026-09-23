"""Synchronize the SVD seating hold, finger release and complete left-arm return."""
import ast
import json
import math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Vector, Quaternion

O = Path(__file__).parent
S = O.parent
D = O / 'Animations'
D.mkdir(exist_ok=True)

def helpers(path, names):
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[]), str(path), 'exec'), globals())

helpers(S / 'SVDCompletion20260923/author_svd.py', ['sample', 'select', 'bake', 'mix'])
helpers(S / 'SVDReloadArm20260923/author_animations.py', ['frame', 'filter_vectors'])
previous = json.loads((S / 'SVDReloadArm20260923/authoring.json').read_text())
fit = json.loads((S / 'SVDMagazineFit20260923/grasp_fit.json').read_text())
opened = {n: Quaternion(q) for n, q in fit['open_basis'].items()}
bpy.context.preferences.filepaths.save_version = 0
report = {}

def ease(t):
    t = max(0., min(1., t))
    return t*t*t*(t*(t*6.-15.)+10.)

def finger_basis(p, n):
    return lr[n].inverted() @ p[parent[n]].inverted() @ p[n]

def hand_targets(poses):
    # Existing seated wrap is the contact anchor, including its thumb opposition.
    seated = poses[240]
    G = seated['WPN_SOCKET_Magazine'].inverted() @ seated['hand_l']
    ready = poses[302]
    return_local = ready['WPN_root'].inverted() @ ready['hand_l']
    closed = {n: finger_basis(seated, n).to_quaternion() for n in fingers}
    targets = []
    for f, old in enumerate(poses):
        p = {n: m.copy() for n, m in old.items()}
        if 240 < f < 302:
            M = old['WPN_SOCKET_Magazine']
            held = M @ G
            # Seat at 240, sustain pressure, open fingers, then withdraw laterally.
            clear = held.copy()
            clear.translation += M.to_3x3() @ Vector((.060, .010, -.012)) * ease((f-254)/14)
            back = ease((f-268)/34)
            H = mix(clear, old['WPN_root'] @ return_local, back)
            H.translation += M.to_3x3() @ Vector((.012, 0, -.012)) * math.sin(math.pi*back)
            p['hand_l'] = H
            for n in fingers:
                digit = n.split('_')[0]
                delay = {'thumb': 0, 'index': 1, 'middle': 2, 'ring': 3, 'pinky': 4}[digit]
                q = closed[n].slerp(opened[n], ease((f-244-delay)/12))
                q = q.slerp(finger_basis(old, n).to_quaternion(), ease((f-284)/18))
                loc, _, scale = finger_basis(old, n).decompose()
                p[n] = p[parent[n]] @ lr[n] @ Matrix.LocRotScale(loc, q, scale)
        targets.append(p)
    return targets

def support_return(original, targets):
    # Retarget the whole arm to the new hand path, measuring lengths from the
    # unmodified source, so moving the wrist cannot change a bone's length.
    cn, un, fn, hn = 'clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l'
    ru = (rest[fn].translation-rest[un].translation).normalized()
    rf = (rest[hn].translation-rest[fn].translation).normalized()
    across = (rest['index_01_l'].translation-rest['pinky_01_l'].translation).normalized()
    rnormal = ru.cross(rf).normalized()
    shoulders, elbows, weights = [], [], []
    for f, (old, p) in enumerate(zip(original, targets)):
        A, E = old[un].translation, old[fn].translation
        T, H = p[hn].translation, p[hn]
        l1, l2 = (E-A).length, (old[hn].translation-E).length
        axis = (T-A).normalized()
        natural = (H.to_quaternion() @ rest[hn].to_quaternion().inverted() @ rf).normalized()
        swing = natural.rotation_difference(axis)
        F = Quaternion().slerp(swing, min(1., math.radians(18)/max(swing.angle, 1e-6))) @ natural
        desired = T-F*l2
        direction = (A-desired).normalized()
        if direction.angle(-F) < math.radians(28):
            pole = (A-E)-F*(A-E).dot(F)
            if pole.length < 1e-5:
                pole = old[un].to_quaternion() @ Vector((1, 0, 0))
                pole -= F*pole.dot(F)
            direction = -F*math.cos(math.radians(28))+pole.normalized()*math.sin(math.radians(28))
        w = ease((f-240)/12)*(1-ease((f-302)/34)) if 240 < f < 336 else 0.
        shoulders.append(A.lerp(desired+direction*l1, w))
        elbows.append(E.lerp(desired, w))
        weights.append(w)
    # Filter correction offsets, not the source animation; the source remains
    # exact at the boundaries and all mechanically attached poses are retained.
    shoulder_delta = filter_vectors([shoulders[f]-p[un].translation for f,p in enumerate(original)])
    elbow_delta = filter_vectors([elbows[f]-p[fn].translation for f,p in enumerate(original)])
    for f, (old, p) in enumerate(zip(original, targets)):
        if not 240 < f < 336:
            continue
        boundary = ease((f-240)/6)*(1-ease((f-330)/6))
        A0, E0 = old[un].translation, old[fn].translation
        A = A0+shoulder_delta[f]*boundary
        desired = E0+elbow_delta[f]*boundary
        T, H = p[hn].translation, p[hn]
        l1, l2 = (E0-A0).length, (old[hn].translation-E0).length
        axis = (T-A).normalized()
        distance = (T-A).length
        if distance > l1+l2-.002:
            A += axis*(distance-(l1+l2-.002))
            distance = (T-A).length
        pole = desired-A
        pole -= axis*pole.dot(axis)
        along = (l1*l1-l2*l2+distance*distance)/(2*distance)
        E = A+axis*along+pole.normalized()*math.sqrt(max(0., l1*l1-along*along))
        U, F = (E-A).normalized(), (T-E).normalized()
        transverse = H.to_quaternion() @ rest[hn].to_quaternion().inverted() @ across
        fq = frame(F, transverse) @ frame(rf, across).inverted() @ rest[fn].to_quaternion()
        carried_forearm = (old[hn].translation-E0).rotation_difference(T-E) @ old[fn].to_quaternion()
        fq = carried_forearm.slerp(fq, weights[f])
        canonical = frame(U, U.cross(F)) @ frame(ru, rnormal).inverted() @ rest[un].to_quaternion()
        carried_upper = (E0-A0).rotation_difference(E-A) @ old[un].to_quaternion()
        uq = carried_upper.slerp(canonical, weights[f]*.55)
        p[cn].translation += A-A0
        p[un] = Matrix.LocRotScale(A, uq, old[un].to_scale())
        p[fn] = Matrix.LocRotScale(E, fq, old[fn].to_scale())
        for segment in [un, fn]:
            for suffix in ['01', '02']:
                n = segment.replace('_l', '_twist_'+suffix+'_l')
                if n in p:
                    p[n] = p[segment] @ rest[segment].inverted() @ rest[n]
    return targets

for family in ['base', 'vertical', 'canted', 'prism', 'angled']:
    source = S / 'SVDReloadArm20260923' / f'SVD_{family}_Editable.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source))
    r = bpy.data.objects['SK_M4_Infima']
    rest = {b.name: b.matrix_local.copy() for b in r.data.bones}
    parent = {b.name: b.parent.name if b.parent else None for b in r.data.bones}
    lr = {n: rest[parent[n]].inverted() @ m if parent[n] else m for n,m in rest.items()}
    fingers = [n for n in rest if n.endswith('_l') and n.startswith(('thumb', 'index', 'middle', 'ring', 'pinky'))]
    for clip in ['reload', 'reload_empty']:
        key = family+'/'+clip
        info = previous[key]
        name = info['name']
        action = bpy.data.actions[name]
        poses = [sample(r, action, f) for f in range(info['frames']+1)]
        result = support_return(poses, hand_targets(poses))
        action.name = 'REFERENCE_BEFORE_SEAT_'+name
        bake(r, result, name.removeprefix('A_SVD_'), 120)
        report[key] = {**info, 'source': str(D/(name+'.fbx')), 'previous_blend': str(source),
            'blend': str(O/f'SVD_{family}_Editable.blend'),
            'changed': 'Left seating sustain, staged finger release, lateral clearance, family-specific regrip and full-arm support after frame 240',
            'phases': {'seat':240, 'sustain_until':244, 'finger_release': [244,260], 'withdraw': [254,268], 'return':[268,302], 'arm_settle_end':336},
            'game_tested':False}
        (O/'authoring.json').write_text(json.dumps(report, indent=2))
        print('SVD_SEAT_AUTHORED', key, flush=True)
    sample(r, bpy.data.actions[previous[family+'/reload']['name']], 246)
    bpy.ops.wm.save_as_mainfile(filepath=str(O/f'SVD_{family}_Editable.blend'))
print('SVD_SEAT_AUTHORING_COMPLETE', len(report), flush=True)
