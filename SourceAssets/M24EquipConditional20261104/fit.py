"""Fit the upper-arm cutout behind the view border without moving the palm."""
from pathlib import Path
exec(compile((Path(__file__).parent/'surface.py').read_text().split("if __name__=='__main__'")[0],'M24 skinned rim evaluator','exec'))
END=18/30;FPS=120
def moved(row,side,turn):
    clav='clavicle_'+side;upper='upperarm_'+side;fore='lowerarm_'+side;elbow=row[fore].translation
    rigid=Matrix.Translation(elbow)@turn.to_matrix().to_4x4()@Matrix.Translation(-elbow)
    out=row.copy()
    for n in names:
        if n==clav or (under(n,upper) and not under(n,fore)):out[n]=rigid@row[n]
    return out
def turn_axis(row,side,C,dir):
    target=C.inverted().to_3x3()@Vector(dir)
    fore=row['lowerarm_'+side].translation
    return (row['upperarm_'+side].translation-fore).cross(target).normalized()
def target(t):
    return 3.3*(1.-smooth((t-.39)/(.60-.39)))
def solve(clip,side,cam):
    grid=np.linspace(0,END,round(END*60)+1)
    rows=[compose(clip,t)[0] for t in grid];C=np.asarray(cam)
    base=[clearance(skin(row,side),C) for row in rows]
    margin=[min(target(t),3.3) for t in grid]
    if all(v>=m for v,m in zip(base,margin)):return None
    # Use one bend direction for the entire draw rather than flipping elbow planes.
    sign=-1. if side=='l' else 1.
    dirs=[(-1.,sign*.30,-1.),(-.85,sign*.75,-1.),(-1.,sign*.25,-.40),(-.60,sign*.20,-1.)]
    candidates=[]
    for direction in dirs:
        deg=[]
        for row,t,baseclear,required in zip(rows,grid,base,margin):
            if baseclear>=required:deg.append(0.);continue
            axis=turn_axis(row,side,cam,direction)
            def visible(a):
                rr=moved(row,side,Quaternion(axis,math.radians(a)))
                return clearance(skin(rr,side),C)>=required
            low=0.;high=3.
            while high<39 and not visible(high):low=high;high+=3.
            if not visible(high):deg.append(90.);continue
            for _ in range(10):
                mid=(low+high)/2.
                if visible(mid):high=mid
                else:low=mid
            deg.append(high)
        candidates.append((max(deg),sum(deg),direction,deg))
    peak,_,direction,angles=min(candidates)
    if peak>=39:raise RuntimeError(f'Cannot clear {side} rim naturally, {peak}')
    # A short anticipatory envelope softens the elbow response while keeping
    # the calibrated idle endpoint and the remainder of the bolt clip exact.
    a=np.asarray(angles);sm=a.copy()
    for k in range(len(a)):
        for j in range(max(0,k-4),min(len(a),k+5)):
            sm[k]=max(sm[k],a[j]*(1.-smooth(abs(j-k)/4)))
    sm*=np.array([1.-smooth((t-.52)/.08) for t in grid])
    return grid,sm,direction,peak,min(base)
def author_side(clip,side,cam):
    sol=solve(clip,side,cam)
    if sol is None:return [],None
    grid,angles,direction,peak,worst=sol
    original={tr['bone']:tr for tr in clip['tracks']}
    bones=['clavicle_'+side,'lowerarm_'+side]
    output={n:{'bone':n,'times':[],'values':[]} for n in bones}
    old={n:{stamp(t):tr['values'][i*10:i*10+10] for i,t in enumerate(tr['times'])} if (tr:=original.get(n)) else {} for n in bones}
    times={stamp(k/FPS) for k in range(round(END*FPS)+1)}
    for n in bones:times.update(old[n])
    for t in sorted(times):
        angle=float(np.interp(t,grid,angles)) if t<END else 0.
        if angle>1e-7:
            row,_=compose(clip,t);rot=Quaternion(turn_axis(row,side,cam,direction),math.radians(angle));out=moved(row,side,rot)
        for n,tr in output.items():
            if t>END+1e-6 and t not in old[n]:continue
            val=old[n][t].copy() if t in old[n] else existing_delta(original.get(n),t)
            if angle>1e-7:
                p,q,s=(K@local(out,n)@K).decompose()
                bp,bq,sc=raw(D['clips'][clip['base']],t,n).decompose()
                delta=q@bq.inverted();delta.normalize()
                if delta.dot(Quaternion((val[6],*val[3:6])))<0:delta.negate()
                if n.startswith('clavicle'):val[:3]=list(p-bp)
                val[3:7]=[delta.x,delta.y,delta.z,delta.w]
            tr['times'].append(t);tr['values'].extend(val)
    return list(output.values()),{'original_min_cm':worst,'peak_swing_deg':peak,'view_direction':direction}
plans={};reports={}
for family in D['profiles']:
    cam=get_cameras(family);plans[family]={};reports[family]={}
    for role in ('equip_ready','equip'):
        clip=entry(family,role);replacement={}
        for side in rims:
            result,stats=author_side(clip,side,cam);replacement.update({x['bone']:x for x in result})
            if stats:reports[family][role+'_'+side]=stats
        if role=='equip_ready':
            result=[replacement.pop(t['bone'],t) for t in clip['tracks']];result.extend(replacement.values())
            plans[family][role]={'base':READY,'duration':duration,'tracks':result}
        elif replacement:plans[family][role]=list(replacement.values())
    print('EQUIP_RIM_FIT',family,reports[family],flush=True)
with gzip.open(O/'families.json.gz','wt',compresslevel=2) as f:json.dump(plans,f,separators=(',',':'))
(O/'fit_report.json').write_text(json.dumps(reports,indent=2))
