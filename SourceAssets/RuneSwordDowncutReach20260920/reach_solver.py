"""Open the held-group downswing arc; retain the accepted grasp and bone lengths."""
import math
from mathutils import Matrix, Vector

TARGET_ANGLE = math.radians(160.)

def smooth(x):
    x = max(0., min(1., x))
    return x*x*x*(10.-15.*x+6.*x*x)

def envelope(t):
    return smooth((t-1.02)/.09)*(1.-smooth((t-1.50)/.45))

def positive(x, width=.002):
    # C1 activation avoids a kink as a moving arm crosses the reach floor.
    if x <= -width: return 0.
    if x >= width: return x
    return (x+width)**2/(4.*width)

def solve(source, parents, t):
    pose = {n:m.copy() for n,m in source.items()}
    weight = envelope(t)
    if weight < 1e-9: return pose, {'weight':0., 'forward_m':0., 'shoulder_m':{'l':0.,'r':0.}}
    arms = {}
    for side in ('l','r'):
        u,f,h = [n+'_'+side for n in ('upperarm','lowerarm','hand')]
        s,e,w = [source[n].translation.copy() for n in (u,f,h)]
        l1,l2 = (e-s).length,(w-e).length
        reach = (w-s).length
        floor = math.sqrt(l1*l1+l2*l2-2.*l1*l2*math.cos(TARGET_ANGLE))
        desired = reach + weight*positive(floor-reach)
        d = w-s
        forward = math.sqrt(max(0.,desired*desired-d.x*d.x-d.z*d.z))-d.y
        arms[side] = (s,e,w,l1,l2,desired,forward)
    # The two palms and the sword share ONE translation. Modest shoulder
    # protraction balances their different positions on the grip.
    delta = Vector((0.,sum(v[-1] for v in arms.values())*.5,0.))
    shoulder_moves = {}
    for side,(s,e,w,l1,l2,reach,_) in arms.items():
        u,f,h = [n+'_'+side for n in ('upperarm','lowerarm','hand')]
        wrist = w+delta
        direction = (wrist-s).normalized()
        shoulder = wrist-direction*reach
        shoulder_moves[side] = (shoulder-s).length
        along = (l1*l1-l2*l2+reach*reach)/(2.*reach)
        # Keep the source anatomical bend plane. Do not roll the elbow around
        # the wrist or impose a symmetric pole on the two different grips.
        pole = e-s
        pole = (pole-direction*pole.dot(direction)).normalized()
        elbow = shoulder+direction*along+pole*math.sqrt(max(0.,l1*l1-along*along))
        for anchor,old_a,old_b,new_a,new_b,names in (
            (u,s,e,shoulder,elbow,(u,'upperarm_twist_01_'+side,'upperarm_twist_02_'+side)),
            (f,e,w,elbow,wrist,(f,'lowerarm_twist_01_'+side,'lowerarm_twist_02_'+side))):
            turn = (old_b-old_a).rotation_difference(new_b-new_a)
            transport = Matrix.Translation(new_a)@turn.to_matrix().to_4x4()@Matrix.Translation(-old_a)
            for n in names: pose[n] = transport@source[n]
        pose['clavicle_'+side].translation += shoulder-s
        pose[h].translation += delta
    pose['WPN_root'].translation += delta
    # All descendants of the palms/weapon follow the same rigid translation.
    # Their parent-local tracks remain untouched on the installed assets.
    translated = {'hand_l','hand_r','WPN_root'}
    for n in source:
        if n not in translated and parents.get(n) in translated:
            pose[n].translation += delta
            translated.add(n)
    return pose, {'weight':weight,'forward_m':delta.y,'shoulder_m':shoulder_moves}
