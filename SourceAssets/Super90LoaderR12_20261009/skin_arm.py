"""Native Super90 arm writeback using the transported V7 skin hinge.

Executed after core, before motion. Keep hand targets/lengths; replace the R11
source-delta twist accumulation with a complete, absolute skin deformation field.
"""
_vrest = {n: Matrix(m) for n, m in json.loads((O/'v7_skin_basis.json').read_text())['rest'].items()}
_warp = {n: Matrix(m) for n, m in json.loads((S/'BenelliM4Super9020261006/authoring.json').read_text())['v7_to_native_warp'].items()}
SKIN = {}
for side in 'lr':
    upper, lower, hand = ('upperarm_'+side, 'lowerarm_'+side, 'hand_'+side)
    vu = _vrest[lower].translation - _vrest[upper].translation
    vf = _vrest[hand].translation - _vrest[lower].translation
    vh = vu.cross(vf).normalized()
    ru = rest[lower].translation - rest[upper].translation
    rf = rest[hand].translation - rest[lower].translation
    hu = (_warp[upper].to_3x3() @ vh).normalized()
    hf = (_warp[lower].to_3x3() @ vh).normalized()
    SKIN[side] = (segment_frame(ru, hu), segment_frame(rf, hf), ru, rf)

# The bare arm really ends beyond upperarm_l; hiding the joint alone leaves its
# open boundary in view. Carry the native mesh boundary with the solved humerus.
from collections import Counter
_mesh = bpy.data.objects['Super90_V7_M4_BareArmsV6']
_edges = Counter(tuple(sorted(e)) for poly in _mesh.data.polygons for e in poly.edge_keys)
_boundary = {i for edge,num in _edges.items() if num == 1 for i in edge}
_cap = []
for i in _boundary:
    v = _mesh.data.vertices[i]
    if v.groups and _mesh.vertex_groups[max(v.groups,key=lambda w:w.weight).group].name == 'upperarm_l':
        _cap.append(v.co.copy()-rest['upperarm_l'].translation)
CAP_CENTRE = sum(_cap, Vector()) / len(_cap)
CAP_RADIUS = max((v-CAP_CENTRE).length for v in _cap)

_old_arm = arm
def wrist_first(source, target, side, initial, weight):
    """Constrain the actual native palm/forearm relation, then support it from
    the torso. A near-camera elbow is not an acceptable substitute for wrist bend.
    Two bounded wrist-cone controls keep contact and native segment lengths exact.
    """
    fu0, ff0, ru, rf = SKIN[side]
    a0 = source['upperarm_'+side].translation
    t = target.translation
    la, lb = ru.length, rf.length
    dh = target.to_quaternion() @ rest['hand_'+side].to_quaternion().inverted()
    neutral = (dh @ rf).normalized()
    by = dh @ (ff0 @ Vector((0,1,0)))
    bz = dh @ (ff0 @ Vector((0,0,1)))
    ac0, tc = cam(a0), cam(t)
    key = side+'_wrist_controls'; prev = pole_context.get(key, (0.,0.))
    def geometry(x):
        r = math.hypot(*x); v = by*x[0]+bz*x[1]
        fdir = Quaternion(v.normalized(), r) @ neutral if r > 1e-8 else neutral
        e = t - lb*fdir
        ud = (e-a0).normalized()
        bend = ud.angle(fdir); bound = max(math.radians(25),min(math.radians(155),bend))
        radial = ud-fdir*ud.dot(fdir)
        if radial.length < 1e-6: radial = by.copy()
        ud = fdir*math.cos(bound)+radial.normalized()*math.sin(bound)
        a = e-la*ud
        h = ud.cross(fdir).normalized()
        df = segment_frame(fdir,h)@ff0.inverted()
        diff = dh@df.inverted()
        tau = (2*math.atan2(Vector((diff.x,diff.y,diff.z)).dot(fdir),diff.w)+math.pi)%(2*math.pi)-math.pi
        return a,e,fdir,tau
    def cost(x):
        if math.hypot(*x) > math.radians(28): return 1e6
        if math.hypot(*(x[i]-prev[i] for i in range(2))) > math.radians(5): return 1e6
        a,e,fd,tau=geometry(x); ac,ec=cam(a),cam(e)
        da=ac-ac0
        du=segment_frame(e-a,(e-a).cross(fd))@fu0.inverted()
        cc=cam(a+du@CAP_CENTRE)
        cap_edge=cc.z+TAN_V*cc.x+100*CAP_RADIUS*math.sqrt(1+TAN_V*TAN_V)
        # cm-space residuals: body support, low elbow, camera clearance,
        # moderate pronation, small wrist control changes.
        return (da.x*.75)**2+(da.y*1.1)**2+(da.z*.8)**2 + \
            (max(0.,cap_edge+1.)*5.)**2 + \
            (max(0.,ac.z-ac0.z-1.)*5.)**2 + \
            (max(0.,ec.z-min(tc.z-4.,-16.))*3.)**2 + \
            (max(0.,12.-ec.x)*3.)**2 + \
            (max(0.,abs(tau)-math.radians(105))*15.)**2 + \
            sum((z*4.)**2 for z in x) + sum(((x[i]-prev[i])*8.)**2 for i in range(2))
    x=tuple(prev)
    for step in (4,2,1,.5,.25):
        d=math.radians(step)
        for repeat in range(2):
            x=min((x,*(tuple(x[k]+(d*s if k==j else 0.) for k in range(2)) for j in range(2) for s in (-1,1))),key=cost)
    pole_context[key]=x
    a,e,fd,tau=geometry(x)
    if weight < 1:
        fa=(t-initial[1]).normalized()
        fd=fa.slerp(fd,weight).normalized()
        e=t-lb*fd
        a=e-la*(initial[1]-initial[0]).normalized().slerp((e-a).normalized(),weight).normalized()
    return a,e

def arm(p, source, target, side, pole_rotation=0., continuous=False, natural_axis=None, hint_weight=0., relax=0., home=0.):
    # Position solve retains native segment lengths and continuous elbow poles.
    st = _old_arm(p, source, target, side, pole_rotation, continuous, natural_axis, hint_weight, relax, home)
    upper, lower, hand = ('upperarm_'+side, 'lowerarm_'+side, 'hand_'+side)
    a, e, t = p[upper].translation.copy(), p[lower].translation.copy(), target.translation.copy()
    blend = min(relax, 1-home)
    if side == 'l' and blend > 0:
        old_a=a.copy()
        a,e=wrist_first(source,target,side,(a,e),blend)
        p['clavicle_'+side].translation += a-old_a
        p[upper].translation=a; p[lower].translation=e
    u, f = e-a, t-e; h = u.cross(f).normalized(); fa = f.normalized()
    fu0, ff0, ru, rf = SKIN[side]
    du = segment_frame(u, h) @ fu0.inverted()
    df = segment_frame(f, h) @ ff0.inverted()
    dh = target.to_quaternion() @ rest[hand].to_quaternion().inverted()
    diff = dh @ df.inverted()
    if diff.w < 0: diff.negate()
    tau = 2 * math.atan2(Vector((diff.x,diff.y,diff.z)).dot(fa), diff.w)
    tau = (tau + math.pi) % (2*math.pi) - math.pi
    branch_key = side+'_skin_branch'
    prev_tau = twist_context.get(branch_key)
    if prev_tau is not None:
        tau = prev_tau + (tau-prev_tau+math.pi)%(2*math.pi)-math.pi
    twist_context[branch_key] = tau
    fore_tau = max(-math.radians(100),min(math.radians(100),tau))
    remainder = tau-fore_tau
    # Share excess rotation coherently across the upper/lower hinge; the wrist
    # still receives the exact target, and no helper stores a lagged delta.
    du = Quaternion(u.normalized(),remainder)@du
    df = Quaternion(fa,remainder)@df
    # Absolute continuous anatomical branch. No accumulation on top of an already
    # twisted idle helper, and no per-frame clamp lag between hand and wrist skin.
    for n in [upper, lower, *skin_stations[side]]:
        if n == upper:
            q = du @ rest[n].to_quaternion(); pos = a
        else:
            station = 0. if n == lower else skin_stations[side][n]
            d = Quaternion(fa, fore_tau * station) @ df
            q = d @ rest[n].to_quaternion()
            off = rest[n].translation - rest[lower].translation - rf * station
            pos = e + f * station + d @ off
        carried = p[n].to_quaternion()
        if carried.dot(q) < 0: q.negate()
        p[n] = Matrix.LocRotScale(p[n].translation.lerp(pos, blend), carried.slerp(q, blend), one)
    p[hand] = ortho(target)
    st['skin_pronation_degrees'] = math.degrees(tau)
    st['shoulder_shift_cm'] = 100*(a-source[upper].translation).length
    st['native_wrist_bend_degrees'] = math.degrees(fa.angle((dh@rf).normalized()))
    return st
