"""Fit opposed thumb silhouettes to each installed mesh and the shared idle."""
from pathlib import Path
exec(compile((Path(__file__).parent/'common_pose.py').read_text(), 'saved geometry', 'exec'))

all_ids = np.asarray([i for i in hand_ids if RIGHT[int(W[i].argmax())] in thumb])
terminal = all_ids[[RIGHT[int(W[i].argmax())] == thumb[2] for i in all_ids]]
parameters = [(0, 'X'), (0, 'Y'), (0, 'Z'), (1, 'Y'), (1, 'Z'), (2, 'Z')]

def bent(row, angles):
    result = dict(row)
    for j, bone in enumerate(thumb):
        p, q, scale = local(row, bone).decompose()
        for (joint, axis), angle in zip(parameters, angles):
            if joint == j:
                q = q @ Quaternion({'X':(1,0,0),'Y':(0,1,0),'Z':(0,0,1)}[axis], math.radians(angle))
        result[bone] = result[parents[bone]] @ Matrix.LocRotScale(p, q, scale)
    return result

def fit(role, stock_names):
    contact = role == 'quick_melee'
    row = rest_row(compose(entry('skeleton_base',role), .25 if contact else 0.)[0])
    tree = [assembly_tree(stock,'Default','mag5') for stock in stock_names]
    stock_bv = [parts[0][0] for parts in tree]
    origin = skin_points(row,terminal,True).mean(axis=0)
    root = np.array(row[thumb[0]].translation)
    forward = 1 if origin[1] >= root[1] else -1
    # Follow the length of the surface. The open stock has space around the
    # cutout; the continuous side of the carbon model has a longer contact.
    slide = 14 if stock_names[0]=='stock' else 20
    goal = origin + np.array((0, forward*slide, -9 if stock_names[0]=='stock' else -6))*.001
    print('THUMB_REFERENCE', role, stock_names[0], root, origin, goal, flush=True)
    def cost(angles, ids):
        result = bent(row, angles)
        points = skin_points(result, ids, True)
        pad = skin_points(result, terminal[::7], True)
        score = .014*sum(a*a for a in angles)
        if contact:
            score += np.linalg.norm((pad.mean(axis=0)-goal)*1000)**2
            for surface in stock_bv:
                distances = sorted(surface.find_nearest(Vector(p))[3]*1000 for p in pad)
                score += .5*(np.mean(distances[:max(1,len(distances)//8)])-1.1)**2
        else:
            score += .3*np.linalg.norm((pad.mean(axis=0)-origin)*1000)**2
        for parts in tree:
            gaps = signed_distance(parts, points, True)
            depth = np.maximum(0., .25-gaps)
            score += 65*depth.max()**2 + 20*(depth**2).mean()
        return float(score)
    a = [0.]*len(parameters)
    for stride, steps in ((11,(10.,6.,3.)),(4,(4.,2.,1.)),(1,(1.5,.75))):
        ids=all_ids[::stride];best=cost(a,ids)
        for step in steps:
            for sweep in range(2):
                for j in range(len(parameters)):
                    for sign in (-1,1):
                        trial=a.copy();trial[j]=max(-28.,min(28.,trial[j]+sign*step))
                        value=cost(trial,ids)
                        if value < best: a,best=trial,value
    result=bent(row,a)
    return {bone:list(local(row,bone).to_quaternion().inverted() @ local(result,bone).to_quaternion()) for bone in thumb}

fit_result = {stock:fit('quick_melee',(stock,stock+'_native')) for stock in ('stock','carbon')}
fit_result['idle'] = fit('idle',('stock','stock_native','carbon','carbon_native'))
(WORK/'thumb_fit.json').write_text(json.dumps(fit_result,indent=2))
print('M24_THUMB_FIT_READY',flush=True)
