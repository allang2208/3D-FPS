"""Swing only the left shoulder around the existing elbow to clear the camera."""
from pathlib import Path
import struct
exec(compile((Path(__file__).parent/'shoulder.py').read_text().split("if __name__=='__main__'")[0],'bolt shoulder surfaces','exec'))

OWNED=('clavicle_l','lowerarm_l')
BUFFER=1.25
FPS=240
def stamp(t):
    return struct.unpack('f',struct.pack('f',t))[0]

def joint_turn(row,camera,direction):
    upper=row['upperarm_l'].translation
    elbow=row['lowerarm_l'].translation
    wish=camera.inverted().to_3x3()@Vector(direction)
    return (upper-elbow).cross(wish).normalized()

def shift(row,axis,radians):
    turn=Quaternion(axis,radians);elbow=row['lowerarm_l'].translation
    rigid=Matrix.Translation(elbow)@turn.to_matrix().to_4x4()@Matrix.Translation(-elbow)
    out=row.copy()
    for n in names:
        if n=='clavicle_l' or (under(n,'upperarm_l') and not under(n,'lowerarm_l')):
            out[n]=rigid@row[n]
    return out

def view(role,cams):
    return (cams['scope'],55.) if role in ('aim','fire') else (cams['hip'],75.)

def plan(row, X, camera, views, direction):
    axis=joint_turn(row,camera,direction)
    elbow=np.asarray(row['lowerarm_l'].translation)
    def margin(angle):
        turn=np.asarray(Quaternion(axis,math.radians(angle)).to_matrix())
        points=(X-elbow)@turn.T+elbow
        return min(clearance(points,transform,fov)[0] for transform,fov in views)
    if margin(0.)>=BUFFER:return 0.
    # A single smooth elbow-plane swing per role avoids alternating between
    # lateral and downward solutions as the rim crosses a screen corner.
    for limit in (6.,12.,18.,24.,32.,42.):
        if margin(limit)>=BUFFER:
            low,high=0.,limit
            for _ in range(11):
                mid=(low+high)*.5
                if margin(mid)<BUFFER:low=mid
                else:high=mid
            return high
    return 90.

def curves(family,role,cams,aim_direction=None):
    clip=entry(family,role);start,end=window(role,clip)
    times=np.linspace(start,end,max(2,round((end-start)*60)+1))
    samples=[]
    for time in times:
        row,_=compose(clip,float(time));samples.append((row,skin_rim(row)))
    camera,fov=view(role,cams)
    views=[(blend_camera(cams['hip'],cams['scope'],a),75.-a*20.) for a in (0.,.25,.5,.75,1.)] if role in ('aim','fire') else [(camera,fov)]
    # Use the same stable swing direction for aim and its fire handoff.
    directions=[(-.9,-.55,-1.),(-1.,-.9,-.6),(-1.,-.35,-1.),(-1.,-1.,-.15),(-.75,-.10,-1.)]
    if role=='fire' and aim_direction:directions=[aim_direction]
    candidates=[]
    for direction in directions:
        angles=np.asarray([plan(row,X,camera,views,direction) for row,X in samples])
        candidates.append((float(np.max(angles)),direction,angles))
    peak,direction,angles=min(candidates,key=lambda x:x[0])
    if peak>=89.:raise ValueError(f'No natural shoulder swing for {family} {role} ({peak})')
    # Close narrow dips between samples and soften the take-up of clearance.
    smooth_angles=angles.copy()
    for i in range(len(angles)):
        for j in range(max(0,i-6),min(len(angles),i+7)):
            smooth_angles[i]=max(smooth_angles[i],angles[j]*(1.-smooth(abs(i-j)/6.)))
    return times,smooth_angles,direction,peak

def key(tr,t):
    p,q,s=sampled(tr['values'],tr['times'],t)
    return [*p,q.x,q.y,q.z,q.w,*s]

def make_tracks(family,role,cams,controls):
    clip=entry(family,role);times,angles,direction,_=controls;start,end=window(role,clip)
    originals={tr['bone']:tr for tr in clip['tracks'] if tr['bone'] in OWNED}
    if len(originals)!=len(OWNED):raise ValueError(f'Missing shoulder tracks: {family}/{role}')
    old_keys={n:{stamp(t):tr['values'][i*10:i*10+10] for i,t in enumerate(tr['times'])} for n,tr in originals.items()}
    # Keep every existing key, including irregular 200 Hz reload keys. Add
    # 240 Hz keys only where rotation is needed and include each 30 Hz base key.
    owned_times={stamp(t) for tr in originals.values() for t in tr['times']}
    for i in range(math.ceil(start*FPS),math.floor(end*FPS)+1):
        t=stamp(i/FPS)
        if max(np.interp(t+j/FPS,times,angles) for j in (-1,0,1))>1e-5:owned_times.add(t)
    owned_times.update((stamp(start),stamp(end)))
    output={n:{'bone':n,'times':[],'values':[]} for n in OWNED}
    camera,_=view(role,cams)
    for t in sorted(owned_times):
        deg=float(np.interp(t,times,angles)) if start<=t<=end else 0.
        if role=='reload_empty':deg*=smooth((t-start)/.13)
        changed=deg>1e-5
        if changed:
            row,_=compose(clip,t)
            out=shift(row,joint_turn(row,camera,direction),math.radians(deg))
        for n,tr in originals.items():
            result=output[n]
            # Do not introduce sampled keys elsewhere in the reload clip.
            if not changed and t not in old_keys[n] and t not in (stamp(start),stamp(end)) and not (start<t<end):continue
            v=old_keys[n][t].copy() if t in old_keys[n] else key(tr,t)
            if changed:
                p,q,_=(K@local(out,n)@K).decompose()
                bp,bq,_=raw(D['clips'][clip['base']],t,n).decompose()
                delta=q@bq.inverted();delta.normalize()
                if delta.dot(Quaternion((v[6],*v[3:6])))<0:delta.negate()
                if n=='clavicle_l':v[:3]=list(p-bp)
                v[3:7]=[delta.x,delta.y,delta.z,delta.w]
            result['times'].append(t);result['values'].extend(v)
    return list(output.values())

patch={};report={}
for family in D['profiles']:
    cameras=get_cameras(family);patch[family]={};report[family]={};aim_direction=None
    for role in ('aim',*roles):
        controls=curves(family,role,cameras,aim_direction)
        times,angles,direction,peak=controls
        if role=='aim':aim_direction=direction
        if not peak:continue
        clip=entry(family,role)
        patch[family][role]=make_tracks(family,role,cameras,controls)
        report[family][role]={'max_swing_deg':peak,'axis_target_camera':direction,'keys':len(patch[family][role][0]['times'])}
    print('BOLT_SHOULDER',family,report[family],flush=True)
with gzip.open(O/'shoulder_tracks.json.gz','wt',compresslevel=1) as fp:json.dump(patch,fp,separators=(',',':'))
(O/'authoring.json').write_text(json.dumps(report,indent=2))
