"""REJECTED AUTHORING EXPERIMENT. Use author_reference.py for the delivered R2.

This native-bind hinge experiment was not installed. It still concentrated
too much rotation at the forearm; retained solely as a local investigation.

Only SVCH quick-melee deltas are produced. The rifle, palms, digits, source
clock, skin weights and all reload entries remain the current saved inputs.
"""
from pathlib import Path
import sys,json,copy
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'ForegripFit20261019'))
from arm_math import *
from scipy.optimize import least_squares
from scipy.ndimage import gaussian_filter1d
O=HERE
ref=matrices(arms['reference']);clip=motion['clips']['quick_melee']
current=json.loads((O/'Inputs/svch_base.json').read_text())
old=np.array([pose('quick_melee',i,current) for i in range(len(clip['times']))])
donor=np.array([comp(matrices(f)) for f in clip['frames']])
u,l,h,c=[ids[n+'_r'] for n in ('upperarm','lowerarm','hand','clavicle')]
L1=np.linalg.norm(old[0,l,:3,3]-old[0,u,:3,3]);L2=np.linalg.norm(old[0,h,:3,3]-old[0,l,:3,3])
ru=unit(ref[l,:3,3]-ref[u,:3,3]);rl=unit(ref[h,:3,3]-ref[l,:3,3]);rn=unit(np.cross(ru,rl))
def frame(x,n):
    x=unit(x);n=unit(n-x*np.dot(n,x));return np.column_stack((x,np.cross(n,x),n))
FU=frame(ru,rn);FL=frame(rl,rn)
def rr(m):return R.from_matrix(rigid(m)[:3,:3])
def support(S,H,angle):
    ax=unit(H-S);d=np.linalg.norm(H-S);along=(L1*L1-L2*L2+d*d)/(2*d)
    pole=unit(np.array([1.,0.,-1.])-ax*np.dot(ax,np.array([1.,0.,-1.])))
    pole=R.from_rotvec(ax*angle).apply(pole)
    E=S+ax*along+pole*np.sqrt(max(.00001,L1*L1-along*along))
    nu=unit(E-S);nl=unit(H-E);nn=unit(np.cross(nu,nl))
    return E,frame(nu,nn)@FU.T,frame(nl,nn)@FL.T
def decompose(Dl,Dh):
    rel=R.from_matrix(Dl.T@Dh).as_quat()
    if rel[3]<0:rel=-rel
    tau=2*np.arctan2(rel[:3]@rl,rel[3])
    swingr=R.from_rotvec(rl*tau).inv()*R.from_matrix(Dl.T@Dh)
    return tau,swingr.as_rotvec()

# Keep the shoulder on the SVD idle body-side support, not on the old
# near-camera elbow trajectory. The support is allowed a small, smooth reach.
anchor=old[0,u,:3,3]+np.array([14.,0.,-28.])
solutions=[];previous=np.array([0.,0.,0.,0.])
for i,p in enumerate(old):
    H=p[h,:3,3];Dh=rigid(p[h])[:3,:3]@rigid(ref[h])[:3,:3].T
    def residual(x):
        S=anchor+x[:3];E,Du,Dl=support(S,H,x[3]);tau,sw=decompose(Dl,Dh)
        # Give axial twist its own cost. Minimising wrist swing alone selected
        # the rejected ~140-degree forearm rotation and the opposite elbow.
        reach=np.linalg.norm(H-S)/(L1+L2)
        return np.r_[sw/np.deg2rad(30),tau/np.deg2rad(55),x[:3]/11.,
            max(0.,reach-.94)*80.,max(0.,E[2]-(H[2]-2.))/5.,
            max(0.,S[0]-E[0]-3.)/6.]
    trials=[]
    for angle in [previous[3],-.8,.0,.8,1.6,-1.6]:
        seed=previous.copy();seed[3]=angle
        fit=least_squares(residual,seed,bounds=([-12,-20,-8,-2.7],[16,10,15,2.7]),max_nfev=70)
        trials.append((sum(residual(fit.x)**2)+.08*(fit.x[3]-previous[3])**2,fit.x))
    previous=min(trials,key=lambda v:v[0])[1];solutions.append(previous)
solutions=np.array(solutions)
solutions[:,:3]=gaussian_filter1d(solutions[:,:3],2.,axis=0,mode='nearest')
solutions[:,3]=gaussian_filter1d(np.unwrap(solutions[:,3]),2.,mode='nearest')

new=[];rolls=[];stats=[]
for i,(p,x) in enumerate(zip(old,solutions)):
    t=clip['times'][i];w=float(ease(0,.10,t)*(1-ease(.70,.9,t)))
    S=anchor+x[:3];H=p[h,:3,3];E,Du,Dl=support(S,H,x[3])
    # Hand position fixes both segment lengths; the entry/recovery elbow plane
    # blends on its two-bone circle instead of lerping through shortened limbs.
    S=(1-w)*p[u,:3,3]+w*S;ax=unit(H-S);d=np.linalg.norm(H-S)
    along=(L1*L1-L2*L2+d*d)/(2*d);rad=np.sqrt(max(0.,L1*L1-along*along))
    original=unit(p[l,:3,3]-S-ax*np.dot(p[l,:3,3]-S,ax))
    wanted=unit(E-S-ax*np.dot(E-S,ax));turn=np.arctan2(ax@np.cross(original,wanted),np.clip(original@wanted,-1,1))
    pole=R.from_rotvec(ax*turn*w).apply(original)
    E=S+ax*along+pole*rad;nu=unit(E-S);nl=unit(H-E);nn=unit(np.cross(nu,nl))
    Du=frame(nu,nn)@FU.T;Dl=frame(nl,nn)@FL.T
    # Reorient the complete segments; their helpers move at their native stations.
    aimU=swing(p[l,:3,3]-p[u,:3,3],E-S);aimL=swing(H-p[l,:3,3],H-E)
    desiredU=Du@rigid(ref[u])[:3,:3];desiredL=Dl@rigid(ref[l])[:3,:3]
    U=Slerp([0,1],R.from_matrix([aimU@rigid(p[u])[:3,:3],desiredU]))([w]).as_matrix()[0]
    L=Slerp([0,1],R.from_matrix([aimL@rigid(p[l])[:3,:3],desiredL]))([w]).as_matrix()[0]
    q=p.copy();q[c,:3,3]+=S-p[u,:3,3]
    for main,start,newstart,rot in [(u,p[u,:3,3],S,U),(l,p[l,:3,3],E,L)]:
        delta=rot@rigid(p[main])[:3,:3].T
        prefix=names[main].rsplit('_',1)[0]
        for j,n in enumerate(names):
            if n.startswith(prefix) and n.endswith('_r'):
                q[j,:3,3]=newstart+delta@(p[j,:3,3]-start)
                q[j,:3,:3]=delta@p[j,:3,:3]
    Dh=rigid(p[h])[:3,:3]@rigid(ref[h])[:3,:3].T
    actualDl=L@rigid(ref[l])[:3,:3].T
    tau,sw=decompose(actualDl,Dh);rolls.append(tau)
    q[h]=p[h];new.append(q)
    stats.append({'frame':i,'weight':w,'wrist_swing_deg':float(np.degrees(np.linalg.norm(sw))),
        'roll_deg':float(np.degrees(tau)),'shoulder':S.tolist(),'elbow':E.tolist()})

# One continuous axial branch for the whole action, shared by both stations.
rolls=np.unwrap(rolls)
for i,q in enumerate(new):
    w=stats[i]['weight'];nl=unit(q[h,:3,3]-q[l,:3,3]);Dl=rigid(q[l])[:3,:3]@rigid(ref[l])[:3,:3].T
    for prefix,share in [('lowerarm_twist_01',1.),('lowerarm_twist_02',.5)]:
        j=ids[prefix+'_r'];target=R.from_rotvec(nl*rolls[i]*share).as_matrix()@Dl@rigid(ref[j])[:3,:3]
        q[j,:3,:3]=Slerp([0,1],R.from_matrix([rigid(q[j])[:3,:3],target]))([w]).as_matrix()[0]*np.linalg.norm(old[i,j,:3,:3],axis=0)
    if i in [0,len(new)-1]:new[i]=old[i].copy()
new=np.array(new)

changed=[j for j,n in enumerate(names) if n.endswith('_r') and n.startswith(('clavicle','upperarm','lowerarm','hand'))]
dest=O/'Profiles';dest.mkdir(exist_ok=True)
for family in ('base','angled','vertical','canted','prism'):
    source=json.loads((O/'Inputs'/('svch_'+family+'.json')).read_text());out=copy.deepcopy(source)
    entry=next(c for c in out['clips'] if c['base']==clip['path']);values={j:[] for j in changed}
    for i,t in enumerate(clip['times']):
        local0=apply(clip['frames'][i],entry,t);local=matrices(local0)
        for j in changed:
            local[j]=relative(new[i,parents[j]],new[i,j]);local[j,:3,:3]=rigid(local[j])[:3,:3]*local0[j,7:]
            v=np.zeros(10);v[:3]=local[j,:3,3]-np.array(clip['frames'][i][j])[:3]
            v[3:7]=(rr(local[j])*R.from_quat(clip['frames'][i][j][3:7]).inv()).as_quat();v[7:]=local0[j,7:]-np.array(clip['frames'][i][j])[7:]
            if values[j] and values[j][-1][3:7]@v[3:7]<0:v[3:7]*=-1
            values[j].append(v)
    entry['tracks']=[tr for tr in entry['tracks'] if ids[tr['bone']] not in changed]
    for j in changed:entry['tracks'].append({'bone':names[j],'times':clip['times'],'values':np.round(values[j],10).ravel().tolist()})
    (dest/(family+'.json')).write_text(json.dumps(out,separators=(',',':')))
np.savez_compressed(O/'poses.npz',before=old,after=new,svd=donor)
(O/'authoring.json').write_text(json.dumps({'samples':stats,'source':'Current SVD source and native V9','mesh_written':False,'source_sequence_written':False},indent=2))
print('Authored five SVCH quick-melee profiles; not installed',flush=True)
print('roll range',np.degrees(rolls).min(),np.degrees(rolls).max(),'maximum wrist swing',max(v['wrist_swing_deg'] for v in stats),flush=True)
