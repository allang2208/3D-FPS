"""Fit the complete support chain at fixed palm contacts, then interpolate joints."""
from rig import *
from scipy.interpolate import PchipInterpolator
from scipy.spatial import ConvexHull
out=pickle.load(open(ROOT/'current_poses.pkl','rb'))
cl,ua,la,ha,arm,hand=indices('l')
box=ix['PKM_Box'];boxids=np.unique(faces[sections==g['slots'].index('M249_Surface__OldBox')]);planes=ConvexHull(vertices[boxids]).equations
foreids=np.array([i for i,ws in enumerate(g['weights']) if sum(v for b,v in ws if names[b].startswith('lowerarm') and names[b].endswith('_l'))>.5])[::3]
upperids=np.unique(faces[sections==g['slots'].index('Skin_UpperArm')]);upperids=upperids[np.array([names[dominant[i]].endswith('_l') for i in upperids])][::3]
def subset(ids):
    groups={}
    for j,i in enumerate(ids):
        for b,v in g['weights'][i]:groups.setdefault(b,np.zeros(len(ids)))[j]=v
    return np.c_[vertices[ids],np.ones(len(ids))],groups
foredata=subset(foreids);upperdata=subset(upperids)
def skin_subset(w,data):
    pts,groups=data;xf=w@invB;v=np.zeros((len(pts),3))
    for b,weights in groups.items():v+=(pts@xf[b,:3,:].T)*weights[:,None]
    return v
def boxmargin(w):
    p=skin_subset(w,foredata);xf=B[box]@np.linalg.inv(w[box]);p=p@xf[:3,:3].T+xf[:3,3]
    return np.max(p@planes[:,:3].T+planes[:,3],axis=1).min()
tanx=np.tan(np.radians(107.512367/2));tany=tanx*9/16
def camera(family,path,times):
    family='base' if family=='bipod' else family
    if path.endswith('_idle'):return None
    key=family+('_empty_60' if path.endswith('_empty') else '_normal_60')
    a=np.fromfile(ROOT.parent/'Wrist34/native_delivered'/(key+'.f32'),np.float32).reshape(-1,6+len(names)*7+14)
    a=a[a[:,1]==2];a=a[[np.argmin(abs(a[:,3]-t)) for t in times]]
    rig=matrix(np.c_[a[:,-14:-7],np.ones((len(a),3))]);eye=matrix(np.c_[a[:,-7:],np.ones((len(a),3))])
    folder=ROOT.parent/'Wrist34'/('geometry_prism_final' if family=='prism' else 'geometry_final')/('box_'+('empty_' if path.endswith('_empty') else 'normal_')+family)
    frames=json.loads((folder/'review.json').read_text(encoding='utf-8-sig'))['frames'];offset=sample(np.array([f['camera'] for f in frames]).ravel(),[f['source'] for f in frames],times)
    return np.linalg.inv(matrix(offset))@np.linalg.inv(eye)@rig
def margin(w,xf):
    v=skin_subset(w,upperdata)@xf[:3,:3].T+xf[:3,3]
    return np.maximum.reduce([-v[:,2]-v[:,0]*tany,-v[:,1]-v[:,0]*tanx,v[:,1]-v[:,0]*tanx,-v[:,0]]).min()
fits={};poses={};report={}
if (ROOT/'left_fits.pkl').exists():fits=pickle.load(open(ROOT/'left_fits.pkl','rb'))
for family in (sys.argv[1:] or list(out)):
    for path,a in out[family].items():
        t=a['times'];old=a['world'];cams=camera(family,path,t);key=(family,path)
        ks=np.unique(np.r_[np.arange(0,len(t),6),len(t)-1]);xs=[];last=np.zeros(4)
        for k in ks:
            w=old[k];minbox=min(.2,boxmargin(w));minvis=min(.30,margin(w,cams[k])) if cams is not None else -999
            def cost(x):
                q=solve(w,x);bendcost=max(0,bend(q)-3)**2*25
                movement=.025*np.linalg.norm(q[ua,:3,3]-w[ua,:3,3])**2+.012*np.linalg.norm(q[la,:3,3]-w[la,:3,3])**2
                return bendcost+movement+.002*np.degrees(x).dot(np.degrees(x))+.005*np.degrees(x-last).dot(np.degrees(x-last))
            def constraints(x):
                q=solve(w,x);length=np.linalg.norm(w[la,:3,3]-w[ua,:3,3])+np.linalg.norm(w[ha,:3,3]-w[la,:3,3]);reach=np.linalg.norm(q[ha,:3,3]-q[ua,:3,3])
                values=[boxmargin(q)-minbox,length*.975-reach]
                if cams is not None:values.append(margin(q,cams[k])-minvis)
                return np.array(values)
            fit=minimize(cost,last,method='SLSQP',bounds=[(-1.5,1.5)]*4,constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=100,ftol=1e-5,eps=1e-5))
            if constraints(fit.x).min()<-.015:
                print('CONSTRAINT_RETRY',family,float(t[k]),constraints(fit.x).tolist(),flush=True)
                retry=minimize(cost,np.zeros(4),method='SLSQP',bounds=[(-1.5,1.5)]*4,constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=150,ftol=1e-5,eps=1e-5))
                if constraints(retry.x).min()>constraints(fit.x).min():fit=retry
            last=fit.x;xs.append(last)
        curve=PchipInterpolator(t[ks],np.array(xs),axis=0);params=curve(t);new=np.array([solve(w,x) for w,x in zip(old,params)])
        final=preserve_local(old,new,[cl]+arm+[ha]);poses[key]=dict(times=t,before=old,after=final,cameras=cams)
        fits[key]=dict(times=t[ks],parameters=np.array(xs));pickle.dump(fits,open(ROOT/'left_fits.pkl','wb'))
        metricsafter=metrics(final,B,names);entry=dict(max_bend_before=float(a['metrics']['wrist_swing'].max()),max_bend_after=float(metricsafter['wrist_swing'].max()),max_palm_position_error_cm=float(np.linalg.norm(final[:,ha,:3,3]-old[:,ha,:3,3],axis=1).max()),max_rotation_step=float(np.degrees(np.linalg.norm(np.diff(params,axis=0),axis=1)).max()))
        report[family+'/'+path.split('.')[-1]]=entry
        print(family,path.split('.')[-1],entry,flush=True)
    pickle.dump(poses,open(ROOT/('left_'+family+'.pkl'),'wb'));poses={}
    (ROOT/('left_'+family+'_report.json')).write_text(json.dumps(report,indent=2));report={}
