from mathutils import Matrix,Vector,Quaternion
import math,bisect,bpy
def matrix(v):
    return Matrix.LocRotScale(Vector(v[:3]), Quaternion((v[6], *v[3:6])), Vector(v[7:10]))

def pack(m):
    p, q, s = m.decompose()
    return [*p, q.x, q.y, q.z, q.w, *s]

def mix(a, b, w):
    pa, qa, sa = a.decompose()
    pb, qb, sb = b.decompose()
    return Matrix.LocRotScale(pa.lerp(pb, w), qa.slerp(qb, w), sa.lerp(sb, w))

def smooth(x):
    x = max(0, min(1, x))
    return x * x * (3 - 2 * x)

def curve(t, keys):
    for (a, x), (b, y) in zip(keys, keys[1:]):
        if t <= b:
            return x + (y - x) * smooth((t - a) / (b - a))
    return keys[-1][1]

def track_at(track, t):
    tt = track['times']
    vv = track['values']
    k = max(0, min(len(tt) - 1, bisect.bisect_right(tt, t) - 1))
    a = vv[k * 10:k * 10 + 10]
    if k == len(tt) - 1:
        return a
    b = vv[(k + 1) * 10:(k + 2) * 10]
    w = (t - tt[k]) / (tt[k + 1] - tt[k])
    qa = Quaternion((a[6], *a[3:6]))
    qb = Quaternion((b[6], *b[3:6]))
    q = qa.slerp(qb, w)
    return [*Vector(a[:3]).lerp(Vector(b[:3]), w), q.x, q.y, q.z, q.w, *Vector(a[7:]).lerp(Vector(b[7:]), w)]

def apply_profile(local, entry, t=0):
    result = {n: m.copy() for n, m in local.items()}
    for track in entry['tracks']:
        n = track['bone']
        v = track_at(track, t)
        p, q, s = result[n].decompose()
        result[n] = Matrix.LocRotScale(p + Vector(v[:3]), Quaternion((v[6], *v[3:6])) @ q, s + Vector(v[7:]))
    return result

def worlds(local):
    result = {}
    for n in D['rest']:
        result[n] = result[parents[n]] @ local[n] if parents[n] in result else local[n]
    return result

def native_pose(local):
    world = worlds(local)
    return {n: r.matrix_world.inverted() @ S @ cm @ world[n] @ S for n in names}

def arm_at(p, old, side, H):
    hn = 'hand_' + side
    delta = H @ old[hn].inverted()
    for n in names:
        if n == hn or (n.endswith('_' + side) and n.startswith(('thumb', 'index', 'middle', 'ring', 'pinky'))):
            p[n] = delta @ old[n]
    a, b = ('upperarm_' + side, 'lowerarm_' + side)
    shoulder = old[a].translation.copy()
    elbow = old[b].translation
    wrist = old[hn].translation
    target = H.translation
    l1 = (elbow - shoulder).length
    l2 = (wrist - elbow).length
    axis = (target - shoulder).normalized()
    dist = (target - shoulder).length
    reach = (l1 + l2) * 0.985
    if dist > reach:
        shoulder += axis * (dist - reach)
        dist = reach
        clavicle = 'clavicle_' + side
        p[clavicle] = old[clavicle].copy()
        p[clavicle].translation += shoulder - old[a].translation
    dist = max(abs(l1 - l2) + 1e-05, dist)
    along = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
    pole = elbow - old[a].translation - axis * (elbow - old[a].translation).dot(axis)
    if pole.length < 1e-07:
        pole = Vector((0, 0, -1))
    newelbow = shoulder + axis * along + pole.normalized() * math.sqrt(max(0, l1 * l1 - along * along))
    qa = (elbow - old[a].translation).rotation_difference(newelbow - shoulder)
    qb = (wrist - elbow).rotation_difference(target - newelbow)
    p[a] = Matrix.LocRotScale(shoulder, qa @ old[a].to_quaternion(), old[a].to_scale())
    p[b] = Matrix.LocRotScale(newelbow, qb @ old[b].to_quaternion(), old[b].to_scale())
    for n in names:
        if n.endswith('_' + side) and n.startswith(('upperarm_twist', 'lowerarm_twist')):
            owner = a if n.startswith('upperarm') else b
            p[n] = p[owner] @ old[owner].inverted() @ old[n]
    if 'ik_hand_' + side in p:
        p['ik_hand_' + side] = H.copy()

def finger_pad(side, digit='thumb'):
    bone = digit + '_03_' + side
    points = []
    for ob in bpy.data.objects:
        if ob.type != 'MESH':
            continue
        vg = ob.vertex_groups.get(bone)
        if not vg:
            continue
        for v in ob.data.vertices:
            if any((g.group == vg.index and g.weight > 0.6 for g in v.groups)):
                points.append(rest[bone].inverted() @ r.matrix_world.inverted() @ ob.matrix_world @ v.co)
    axis = Vector((0, 1, 0))
    points.sort(key=lambda v: v.dot(axis))
    distal = points[-max(1, len(points) // 3):]
    return sum(distal, Vector()) / len(distal) if distal else Vector((0, 0.02, 0))

def finger_at(p, side, pad, target, weight, digit='thumb', metacarpal=False):
    chain = [digit + '_%02d_%s' % (i, side) for i in (1, 2, 3)]
    if metacarpal:
        chain.insert(0, digit + '_metacarpal_' + side)
    old = {n: p[n].copy() for n in chain}
    for _ in range(35):
        for i in reversed(range(len(chain))):
            pivot = p[chain[i]].translation
            tip = p[chain[-1]] @ pad
            a = tip - pivot
            b = target - pivot
            if min(a.length, b.length) < 1e-07:
                continue
            q = a.rotation_difference(b)
            q = Quaternion().slerp(q, 0.65)
            delta = Matrix.Translation(pivot) @ q.to_matrix().to_4x4() @ Matrix.Translation(-pivot)
            for n in chain[i:]:
                p[n] = delta @ p[n]
            if metacarpal and i == 0:
                n = chain[0]
                parent = p[parents[n]]
                local = parent.inverted() @ p[n]
                source = parent.inverted() @ old[n]
                angle = source.to_quaternion().rotation_difference(local.to_quaternion()).angle
                if angle > math.radians(25):
                    bounded = Matrix.LocRotScale(local.translation, source.to_quaternion().slerp(local.to_quaternion(), math.radians(25) / angle), local.to_scale())
                    correction = parent @ bounded @ p[n].inverted()
                    for fn in chain:
                        p[fn] = correction @ p[fn]
    solved_local = {n: p[parents[n]].inverted() @ p[n] for n in chain}
    previous = p[parents[chain[0]]]
    for n in chain:
        parent = parents[n]
        base = old[parent] if parent in old else p[parent]
        authored = solved_local[n]
        source = base.inverted() @ old[n]
        m = mix(source, authored, weight)
        m.translation = source.translation
        p[n] = previous @ m
        previous = p[n]
    return (p[chain[-1]] @ pad - target).length
