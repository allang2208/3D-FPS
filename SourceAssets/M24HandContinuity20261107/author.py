"""Author the two visual stock variants against the saved right-hand tracks."""
from pathlib import Path
import copy
exec(compile((Path(__file__).parent/'common_pose.py').read_text(), 'V9 motion', 'exec'))
fitted = {kind:{n:Quaternion(q) for n,q in values.items()} for kind,values in json.loads((WORK/'thumb_fit.json').read_text()).items()}
fps = 240
times = [i/fps for i in range(217)]
digits = ('middle','ring','pinky','index','thumb')
windows = {'middle':(.605,.714),'ring':(.624,.734),'pinky':(.644,.753),
           'index':(.635,.729),'thumb':(.623,.731)}
finger_bones = {d:[f'{d}_{j:02}_r' for j in (1,2,3)] for d in digits}
joint_ids = {d:np.array([i for i in hand_ids if RIGHT[int(W[i].argmax())] in finger_bones[d]])[::7] for d in digits}
identity = Quaternion()

def locomotion_clock(rows):
    end = 48
    distance = [0.]
    previous = None
    for i in range(end+1):
        pose = rows[i]
        hand = rest['WPN_root'] @ pose['WPN_root'].inverted() @ pose['hand_r']
        if previous is not None:
            # Include angular motion and time so a stationary opening hand
            # keeps a finite interval even when its wrist barely travels.
            qa, qb = previous.to_quaternion(),hand.to_quaternion()
            angle = 2*math.acos(min(1.,abs(qa.dot(qb))))
            distance.append(distance[-1] + (hand.translation-previous.translation).length + .026*angle + .0013)
        previous = hand
    def sample(t):
        if t <= 0 or t >= times[end]: return t
        duration = times[end]; ramp = .031
        def start(x):
            return .5*(x - ramp/math.pi*math.sin(math.pi*x/ramp))
        if t < ramp: area = start(t)
        elif t > duration-ramp: area = duration-ramp-start(duration-t)
        else: area = t-ramp*.5
        at = distance[-1]*area/(duration-ramp)
        upper = min(end,max(1,bisect.bisect_left(distance,at)))
        part = (at-distance[upper-1])/(distance[upper]-distance[upper-1])
        return (upper-1+part)/fps
    return sample

def transport_pose(current,source):
    gun = current['WPN_root'] @ source['WPN_root'].inverted()
    shoulder = current['upperarm_r'].translation
    shift = shoulder - (gun @ source['upperarm_r']).translation
    aligned = Matrix.Translation(shift) @ gun
    out = dict(current)
    for n in owned:
        if n != 'clavicle_r': out[n] = aligned @ source[n]
    return move_hand(out, -shift)

def set_return(pose, d, t, span, opened, closed, weight):
    first,last=span
    for j, n in enumerate(finger_bones[d]):
        # Distal joints finish after the proximal joint.
        u=smooth((t-first-j*.004)/(last-first))
        base=local(pose,n)
        loc=lerp(opened[n],closed[n],u)
        if weight<1.:loc=lerp(base, loc, weight)
        yield n,loc

def return_weight(t):
    return smooth((t-.553)/.032)*(1.-smooth((t-.768)/.032))

def window_fit(rows, family, opened, closed):
    kind=next((k for k in ('balanced','phantom','stable') if family.endswith('_'+k)), 'Default')
    parts=[assembly_tree(k,kind,'mag10' if 'mag10' in family else 'mag5') for k in
           (('stock','carbon','stock_native','carbon_native') if kind=='Default' else ('stock','carbon'))]
    samples=[(times[i],rest_row(rows[i])) for i in range(142,183,3)]
    output={}
    for digit,(start,end) in windows.items():
        def penalty(delay):
            total=0.;peak=0.
            for t,pose in samples:
                out=dict(pose)
                for n,loc in set_return(pose,digit,t,(start+delay,end+delay),opened,closed,return_weight(t)):
                    out[n]=out[parents[n]]@loc
                pts=skin_points(out,joint_ids[digit],True)
                for tree in parts:
                    depth=np.maximum(0.,.15-signed_distance(tree,pts,True))
                    peak=max(peak,float(depth.max()));total+=float((depth*depth).mean())
            return 18*peak*peak + total + (delay/.012)**2
        delay=min((0.,.008,-.008,.016),key=penalty)
        output[digit]=(start+delay,end+delay)
    return output

def encode(clip, bone, t, loc, previous):
    p,q,s=(K@loc@K).decompose()
    bp,bq,bs=raw(D['clips'][clip['base']],t,bone).decompose()
    dq=q@bq.inverted();dq.normalize()
    if previous is not None and dq.dot(previous)<0:dq.negate()
    return [*(p-bp),dq.x,dq.y,dq.z,dq.w,*(s-bs)],dq

def fixed_idle(clip):
    result=copy.deepcopy(clip)
    for track in result['tracks']:
        n=track['bone']
        if n not in thumb:continue
        values=[];last=None
        for t in track['times']:
            p,q,s=raw(D['clips'][clip['base']],t,n).decompose()
            dp,dq,ds=sampled(track['values'],track['times'],t)
            loc=K@Matrix.LocRotScale(p+dp,dq@q,s+ds)@K
            p,q,s=loc.decompose()
            key,last=encode(clip,n,t,Matrix.LocRotScale(p,q@fitted['idle'][n],s),last)
            values.extend(key)
        track['values']=values
    return result

def result_clip(original, values):
    result=dict(original);new_tracks={n:{'bone':n,'times':times,'values':v} for n,v in values.items()}
    result['tracks']=[new_tracks.pop(tr['bone'],tr) for tr in original['tracks']]+list(new_tracks.values())
    return result

for family in D['profiles']:
    clip=entry(family,'quick_melee')
    rows=[compose(clip,t)[0] for t in times]
    clock=locomotion_clock(rows)
    open_pose=rows[154];closed_pose=rows[179]
    opened={n:local(open_pose,n) for bones in finger_bones.values() for n in bones}
    closed={n:local(closed_pose,n) for n in opened}
    spans=window_fit(rows,family,opened,closed)
    default=family in ('skeleton_base','skeleton_mag10')
    values={n:[] for n in owned};carbon_values={n:[] for n in thumb};last={};last_carbon={}
    for i,t in enumerate(times):
        at=clock(t);current=rows[i]
        pose=transport_pose(current,compose(clip,at)[0]) if abs(at-t)>1e-7 else current
        locs={n:local(pose,n) for n in owned};w=return_weight(t)
        if w:
            for digit in digits:locs.update(set_return(pose,digit,t,spans[digit],opened,closed,w))
        held=smooth((at-.097)/.058)*(1.-smooth((t-.404)/.095))
        idle_weight=(1.-smooth(at/.042)+smooth((t-.677)/.073)) if default else 0.
        for n in thumb:
            p,q,s=locs[n].decompose()
            q=q@identity.slerp(fitted['idle'][n],idle_weight)
            for stock in ('stock','carbon'):
                m=Matrix.LocRotScale(p,q@identity.slerp(fitted[stock][n],held),s)
                if stock=='stock':locs[n]=m
                else:
                    key,last_carbon[n]=encode(clip,n,t,m,last_carbon.get(n))
                    carbon_values[n].extend(key)
        for n in owned:
            key,last[n]=encode(clip,n,t,locs[n],last.get(n))
            values[n].extend(key)
    result={'stock':result_clip(clip,values),'carbon':result_clip(clip,{**values,**carbon_values}),'return_windows':spans}
    if default:result['idle']=fixed_idle(entry(family,'idle'))
    with gzip.open(WORK/(family+'.json.gz'),'wt',compresslevel=1) as output:
        json.dump(result,output,separators=(',',':'))
    print('M24_HAND_AUTHORED',family,flush=True)
