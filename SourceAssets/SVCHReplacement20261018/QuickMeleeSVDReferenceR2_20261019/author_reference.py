"""Adapt the current SVD complete arm, including its segment roll, to SVCH.

The SVD contact support is the reference. Its old recovery elbow reversal is
replaced by a continuous body-side support return, with actual V9 cut-edge
clearance. Palms, fingers, weapon, lengths and mechanical clocks are inputs.
"""
from surface import *
from scipy.optimize import least_squares
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter1d
from scipy.sparse import lil_matrix
import copy
from collections import Counter

clip=motion['clips']['quick_melee'];times=np.array(clip['times'])
current=json.loads((O/'Inputs/svch_base.json').read_text())
old=np.array([pose('quick_melee',i,current) for i in range(len(times))])
svd=np.array([comp(matrices(f)) for f in clip['frames']])
u,l,h,c=[ids[n+'_r'] for n in ('upperarm','lowerarm','hand','clavicle')]
L1=np.linalg.norm(old[0,l,:3,3]-old[0,u,:3,3]);L2=np.linalg.norm(old[0,h,:3,3]-old[0,l,:3,3])
armids=[j for j,n in enumerate(names) if n.endswith('_r') and n.startswith(('clavicle','upperarm','lowerarm','hand'))]
def blend(a,b,w):return Slerp([0,1],R.from_matrix([a,b]))([float(w)]).as_matrix()[0]
def mix(a,b,w):
    m=a.copy();m[:3,3]=a[:3,3]*(1-w)+b[:3,3]*w
    m[:3,:3]=blend(rigid(a)[:3,:3],rigid(b)[:3,:3],w)*np.linalg.norm(a[:3,:3],axis=0);return m
def twist(a,axis):
    q=R.from_matrix(a).as_quat()
    if q[3]<0:q=-q
    return 2*np.arctan2(q[:3]@unit(axis),q[3])
axis=unit(ref[h,:3,3]-ref[l,:3,3]);axislocal=rigid(ref[l])[:3,:3].T@axis
relHand=rigid(ref[l])[:3,:3].T@rigid(ref[h])[:3,:3]
source=[]
for i,p in enumerate(svd):
    # Start returning before the source elbow flips upward at frames 65-75.
    w=float(ease(48,98,i));q=p.copy()
    if i>=48:
        for j in armids:q[j]=mix(svd[48,j],svd[-1,j],w)
    # Maintain SVCH's current pistol-grip placement and small hand orientation.
    delta=rigid(old[i,h])@np.linalg.inv(rigid(p[h]))
    for j in armids:q[j]=delta@q[j]
    q[h]=old[i,h]
    source.append(q)
source=np.array(source)

# Actual accepted V9 shoulder opening. No geometry/weight edit or hidden arm.
_,weld=np.unique(np.round(V,5),axis=0,return_inverse=True)
tr=weld[np.array(arms['triangles'])];edges=Counter(tuple(sorted((int(t[k]),int(t[(k+1)%3])))) for t in tr for k in range(3) if t[k]!=t[(k+1)%3])
boundary=np.unique([v for e,count in edges.items() if count==1 for v in e])
upperverts=np.flatnonzero([names[j].endswith('_r') and names[j].startswith(('upperarm','clavicle')) for j in dom])
cut=np.intersect1d(np.flatnonzero(np.isin(weld,boundary)),upperverts)
near=np.flatnonzero([names[j].endswith('_r') and names[j].startswith(('upperarm','lowerarm','clavicle')) for j in dom])[::13]
ty=np.tan(np.deg2rad(75/2));aspect=2.65
def camera(v):return np.c_[10-v[:,1],v[:,0],v[:,2]-5]
def frame_pose(i,x):
    p=old[i].copy();s=source[i];H=p[h,:3,3]
    S=s[u,:3,3]+x[:3];d=np.linalg.norm(H-S);ax=unit(H-S)
    # Fixed native lengths with a bent, reachable elbow.
    length=np.clip(d,22.,(L1+L2)*.94);S+=ax*(d-length);d=length
    pole=unit(s[l,:3,3]-S-ax*np.dot(s[l,:3,3]-S,ax));pole=R.from_rotvec(ax*x[3]).apply(pole)
    along=(L1*L1-L2*L2+d*d)/(2*d);E=S+ax*along+pole*np.sqrt(max(0,L1*L1-along*along))
    Du=swing(s[l,:3,3]-s[u,:3,3],E-S);Dl=swing(s[h,:3,3]-s[l,:3,3],H-E)
    p[c]=s[c].copy();p[c,:3,3]+=S-s[u,:3,3]
    for prefix,main,start,newstart,drot in [('upperarm',u,s[u,:3,3],S,Du),('lowerarm',l,s[l,:3,3],E,Dl)]:
        for j,n in enumerate(names):
            if n.startswith(prefix) and n.endswith('_r'):
                p[j,:3,3]=newstart+drot@(s[j,:3,3]-start);p[j,:3,:3]=drot@s[j,:3,:3]
    L=rigid(p[l])[:3,:3];Hp=rigid(p[h])[:3,:3]
    roll=twist(L.T@Hp@relHand.T,axislocal)
    for prefix,share in [('lowerarm_twist_01',1.),('lowerarm_twist_02',.5)]:
        j=ids[prefix+'_r'];rel=rigid(ref[l])[:3,:3].T@rigid(ref[j])[:3,:3]
        p[j,:3,:3]=L@R.from_rotvec(axislocal*roll*share).as_matrix()@rel*np.linalg.norm(old[i,j,:3,:3],axis=0)
    return p,S,E,H,roll

active=ease(0,.065,times)*(1-ease(.76,.9,times))
knots=list(range(0,len(times),2));controls=[];prev=np.zeros(4)
lo=np.array([-15,-15,-18,-1.05]);hi=np.array([18,18,12,1.05])
for i in knots:
    if active[i]<1e-7:controls.append(np.zeros(4));prev=np.zeros(4);continue
    guess=prev.copy()
    def residual(x):
        p,S,E,H,roll=frame_pose(i,x)
        cp=camera(skin(p,cut));np_=camera(skin(p,near))
        # Off the right/bottom edge at both 16:9 and the user's ultrawide view.
        distance=np.maximum(cp[:,1]-cp[:,0]*ty*aspect,-cp[:,2]-cp[:,0]*ty)
        opening=np.maximum(0,1.5-distance)*ease(0,5,cp[:,0])
        proximity=np.maximum(0,13.-np.linalg.norm(np_,axis=1))
        e0=source[i,l,:3,3]
        return np.r_[opening/.12,proximity/.7,x[:3]/np.array([8,8,10]),x[3]/.65,
            (x-guess)/np.array([6,6,6,.6]),max(0,abs(roll)-np.deg2rad(85))/np.deg2rad(12),
            max(0,E[2]-H[2]+1.)/6.]
    fit=least_squares(residual,np.clip(guess,lo+1e-5,hi-1e-5),bounds=(lo,hi),max_nfev=55,ftol=2e-5,xtol=2e-5,gtol=2e-5)
    controls.append(fit.x);prev=fit.x
dense=PchipInterpolator(times[knots],np.array(controls),axis=0)(times)
new=[];rows=[]
for i,x in enumerate(dense):
    p,S,E,H,roll=frame_pose(i,x);w=float(active[i])
    # Blend source support in component orientation, then re-project the two
    # segments. Only the hand's local compensation changes the hierarchy.
    if w<1.:
        startS=old[i,u,:3,3];startE=old[i,l,:3,3];S=startS*(1-w)+S*w
        ax=unit(H-S);d=np.linalg.norm(H-S);a=(L1*L1-L2*L2+d*d)/(2*d)
        v0=unit(startE-S-ax*np.dot(startE-S,ax));v1=unit(E-S-ax*np.dot(E-S,ax))
        turn=np.arctan2(ax@np.cross(v0,v1),v0@v1);E=S+ax*a+R.from_rotvec(ax*turn*w).apply(v0)*np.sqrt(max(0,L1*L1-a*a))
        p[c]=mix(old[i,c],p[c],w);p[c,:3,3]=old[i,c,:3,3]+S-startS
        for prefix,main,child,newstart,newend in [('upperarm',u,l,S,E),('lowerarm',l,h,E,H)]:
            for j,n in enumerate(names):
                if n.startswith(prefix) and n.endswith('_r'):
                    U0=swing(old[i,child,:3,3]-old[i,main,:3,3],newend-newstart)@rigid(old[i,j])[:3,:3]
                    U1=swing(p[child,:3,3]-p[main,:3,3],newend-newstart)@rigid(p[j])[:3,:3]
                    rot=blend(U0,U1,w);p[j,:3,:3]=rot*np.linalg.norm(old[i,j,:3,:3],axis=0)
            # Native translations are kept on the rotated segment, not blended
            # through a chord which shortens the arm during the handoff.
            delta=rigid(p[main])[:3,:3]@rigid(old[i,main])[:3,:3].T
            for j,n in enumerate(names):
                if n.startswith(prefix) and n.endswith('_r'):p[j,:3,3]=newstart+delta@(old[i,j,:3,3]-old[i,main,:3,3])
        p[h]=old[i,h]
    if i in [0,len(times)-1]:p=old[i].copy()
    new.append(p)
    rows.append({'frame':i,'roll_deg':float(np.degrees(roll)),'support_offset_cm':x[:3].tolist(),'pole_degrees':float(np.degrees(x[3]))})
new=np.array(new)
# SVD's accelerated entry also contains a steep support turn. Smooth the
# support only at authoring time, reprojecting at the original lengths; no
# runtime lag or secondary action clock is added to the weapon/palms.
rough=new.copy();shoulders=gaussian_filter1d(rough[:,u,:3,3],2.5,axis=0,mode='nearest')
elbows=gaussian_filter1d(rough[:,l,:3,3],2.5,axis=0,mode='nearest')
for i,p in enumerate(rough):
    edge=float(ease(0,5,i)*(1-ease(len(times)-7,len(times)-1,i)))
    S=p[u,:3,3]*(1-edge)+shoulders[i]*edge;H=p[h,:3,3];ax=unit(H-S);d=np.linalg.norm(H-S)
    a=(L1*L1-L2*L2+d*d)/(2*d);guide=p[l,:3,3]*(1-edge)+elbows[i]*edge
    E=S+ax*a+unit(guide-S-ax*np.dot(guide-S,ax))*np.sqrt(max(0,L1*L1-a*a))
    q=p.copy();q[c,:3,3]+=S-p[u,:3,3]
    indices=np.arange(max(0,i-7),min(len(times),i+8));weights=np.exp(-.5*((indices-i)/2.5)**2)
    for prefix,main,child,A,B in [('upperarm',u,l,S,E),('lowerarm',l,h,E,H)]:
        rotations=R.from_matrix(rigid(rough[indices,main])[:,:3,:3]);mean=rotations.mean(weights).as_matrix()
        mean=blend(rigid(p[main])[:3,:3],mean,edge)
        localaxis=rigid(p[main])[:3,:3].T@unit(p[child,:3,3]-p[main,:3,3])
        mainrot=swing(mean@localaxis,B-A)@mean;delta=mainrot@rigid(p[main])[:3,:3].T
        for j,n in enumerate(names):
            if n.startswith(prefix) and n.endswith('_r'):
                q[j,:3,3]=A+delta@(p[j,:3,3]-p[main,:3,3]);q[j,:3,:3]=delta@p[j,:3,:3]
    if i in (0,len(times)-1):q=old[i].copy()
    new[i]=q
# Solve the elbow directions across the whole action. SVD's hand path contains
# a fast entry, so a per-frame nearest elbow alone still reverses sharply.
# The two tangent controls keep every elbow exactly L2 away from its palm.
guide=new.copy();Hs=guide[:,h,:3,3];Es=guide[:,l,:3,3]
dirs=np.array([unit(e-hand) for e,hand in zip(Es,Hs)])
tx=np.array([unit(np.cross(v,[0.,0.,1.])) for v in dirs]);ty_=np.cross(dirs,tx)
count=len(times)
def elbows_from(x):
    v=dirs+tx*x[:,0,None]+ty_*x[:,1,None];v/=np.linalg.norm(v,axis=1)[:,None]
    return Hs+L2*v
def sequence_residual(flat):
    x=flat.reshape(count,2);E=elbows_from(x)
    result=np.zeros((count,9));result[:,:3]=(E-Es)/7.
    result[1:,3:6]=np.diff(E,axis=0)/5.
    result[1:-1,6:9]=np.diff(E,n=2,axis=0)/.7
    return np.r_[result.ravel(),x[0]*1000.,x[-1]*1000.]
sparse=lil_matrix((count*9+4,count*2),dtype=int)
for i in range(count):
    for j in range(max(0,i-1),min(count,i+2)):sparse[i*9:(i+1)*9,j*2:j*2+2]=1
sparse[-4:-2,:2]=1;sparse[-2:,-2:]=1
fit=least_squares(sequence_residual,np.zeros(count*2),bounds=(-.6,.6),jac_sparsity=sparse.tocsr(),max_nfev=90,ftol=1e-6,xtol=1e-6,gtol=1e-6)
smoothed=elbows_from(fit.x.reshape(count,2))
for i,p in enumerate(guide):
    E=smoothed[i];H=p[h,:3,3];S=E+L1*unit(p[u,:3,3]-E);q=p.copy()
    q[c,:3,3]+=S-p[u,:3,3]
    for prefix,main,child,A,B in [('upperarm',u,l,S,E),('lowerarm',l,h,E,H)]:
        delta=swing(p[child,:3,3]-p[main,:3,3],B-A)
        for j,n in enumerate(names):
            if n.startswith(prefix) and n.endswith('_r'):
                q[j,:3,3]=A+delta@(p[j,:3,3]-p[main,:3,3]);q[j,:3,:3]=delta@p[j,:3,:3]
    if i in (0,count-1):q=old[i].copy()
    new[i]=q
# Distribute the residual palm roll on a continuous branch after smoothing.
rolls=[]
for p in new:rolls.append(twist(rigid(p[l])[:3,:3].T@rigid(p[h])[:3,:3]@relHand.T,axislocal))
rolls=np.unwrap(rolls)
for i,p in enumerate(new):
    if i in (0,len(times)-1):continue
    for prefix,share in [('lowerarm_twist_01',1.),('lowerarm_twist_02',.5)]:
        j=ids[prefix+'_r'];rel=rigid(ref[l])[:3,:3].T@rigid(ref[j])[:3,:3]
        target=rigid(p[l])[:3,:3]@R.from_rotvec(axislocal*rolls[i]*share).as_matrix()@rel
        p[j,:3,:3]=blend(rigid(p[j])[:3,:3],target,float(active[i]))*np.linalg.norm(old[i,j,:3,:3],axis=0)
dest=O/'Profiles';dest.mkdir(exist_ok=True)
for family in ('base','angled','vertical','canted','prism'):
    src=json.loads((O/'Inputs'/('svch_'+family+'.json')).read_text());out=copy.deepcopy(src)
    entry=next(c for c in out['clips'] if c['base']==clip['path']);values={j:[] for j in armids}
    for i,t in enumerate(times):
        local0=apply(clip['frames'][i],entry,t)
        for j in armids:
            local=relative(new[i,parents[j]],new[i,j]);v=np.zeros(10)
            v[:3]=local[:3,3]-np.array(clip['frames'][i][j])[:3]
            v[3:7]=(R.from_matrix(rigid(local)[:3,:3])*R.from_quat(clip['frames'][i][j][3:7]).inv()).as_quat()
            v[7:]=local0[j,7:]-np.array(clip['frames'][i][j])[7:]
            if values[j] and values[j][-1][3:7]@v[3:7]<0:v[3:7]*=-1
            values[j].append(v)
    entry['tracks']=[tr for tr in entry['tracks'] if ids[tr['bone']] not in armids]
    for j in armids:entry['tracks'].append({'bone':names[j],'times':times.tolist(),'values':np.round(values[j],10).ravel().tolist()})
    (dest/(family+'.json')).write_text(json.dumps(out,separators=(',',':')))
np.savez_compressed(O/'poses.npz',before=old,after=new,svd=svd)
(O/'authoring-reference.json').write_text(json.dumps({'method':'SVD complete segment roll and support; continuous recovery; V9 actual cut-edge clearance','samples':rows,'mesh_written':False,'source_sequence_written':False},indent=2))
print('SVCH SVD-reference profiles authored',flush=True)
