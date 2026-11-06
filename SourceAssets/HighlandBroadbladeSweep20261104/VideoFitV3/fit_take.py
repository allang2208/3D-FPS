"""Fit the visible screen landmarks of the 60 Hz take on each Highland grasp.
Depth is regularized by fixed forearm lengths, a mobile shoulder and palm alignment.
The same observations drive both hands, the sword and the silhouettes of both elbows.
"""
from pathlib import Path
import json
import cv2
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix
from scipy.spatial.transform import Rotation

HERE = Path(__file__).resolve().parent
TAKE = HERE.parent
KEYS = np.loadtxt(HERE / 'landmarks.txt', comments='#', encoding='utf-8-sig')
FRAMES = np.arange(int(KEYS[0, 0]), int(KEYS[-1, 0]) + 1)
FOCAL = 90 / np.tan(np.deg2rad(75 / 2))
FLIP = np.diag([1., -1., 1.])

def unit(vector):
    return vector / np.maximum(1e-7, np.linalg.norm(vector, axis=-1, keepdims=True))

def project(point):
    depth = np.maximum(point[:, 1], 2.)
    return np.column_stack((160 + FOCAL * point[:, 0] / depth, 90 - FOCAL * point[:, 2] / depth))

def read_observations():
    keys = KEYS.copy()
    # The guard is an undirected line. Unwrap its orientation before interpolation.
    keys[:, 14] = np.rad2deg(np.unwrap(np.deg2rad(keys[:, 14]) * 2)) / 2
    samples = PchipInterpolator(keys[:, 0], keys[:, 1:], axis=0)(FRAMES)
    video = cv2.VideoCapture(str(TAKE / 'ReferenceV2/kubold-indexed.mp4'))
    video.set(cv2.CAP_PROP_POS_FRAMES, int(FRAMES[0]))
    gray = []
    for frame in FRAMES:
        ok, image = video.read()
        if not ok: raise RuntimeError(f'Missing reference frame {frame}')
        gray.append(cv2.resize(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), (640,360)))
    # Keep manual labels at the anchors. Between them use bidirectional image flow
    # only where each direction independently lands back on the opposite label.
    for a, b in zip(keys[:-1], keys[1:]):
        i, j = int(a[0]-FRAMES[0]), int(b[0]-FRAMES[0]); pts0=a[1:11].reshape(-1,2); pts1=b[1:11].reshape(-1,2)
        paths=[]; valid=np.ones(5,dtype=bool)
        for start, stop, step, pts in [(i,j,1,pts0),(j,i,-1,pts1)]:
            seq=[np.float32(pts*2).reshape(-1,1,2)]
            for k in range(start,stop,step):
                next_pts,st,_=cv2.calcOpticalFlowPyrLK(gray[k],gray[k+step],seq[-1],None,winSize=(23,23),maxLevel=3)
                seq.append(next_pts); valid &= st.ravel().astype(bool)
            path=np.array(seq)[:,:,0,:]/2; path=path if step==1 else path[::-1]; paths.append(path)
        valid &= (np.linalg.norm(paths[0][-1]-pts1,axis=1)<6)&(np.linalg.norm(paths[1][0]-pts0,axis=1)<6)
        valid &= ((pts0>[2,2])&(pts0<[318,178])&(pts1>[2,2])&(pts1<[318,178])).all(axis=1)
        for k in range(1,j-i):
            u=k/(j-i); observed=(1-u)*paths[0][k]+u*paths[1][k]; xy=samples[i+k,:10].reshape(-1,2); xy[valid]=observed[valid]
    return samples

OBS = read_observations()
N = len(FRAMES)

def rotation_matrix(angles):
    yaw,pitch,roll=angles.T
    forward=np.stack((np.sin(yaw)*np.cos(pitch),np.cos(yaw)*np.cos(pitch),np.sin(pitch)),axis=1)
    across=np.stack((-np.cos(yaw),np.sin(yaw),np.zeros(N)),axis=1)
    normal=np.cross(forward,across)
    across=across*np.cos(roll)[:,None]+normal*np.sin(roll)[:,None]
    return np.stack((across,np.cross(forward,across),forward),axis=-1)

def fit(name):
    folder=TAKE/'Review/ReferenceV2'/(name+'IdleEntry')
    source=json.loads((folder/'surface.json').read_text(encoding='utf-8-sig'))['frames'][0]
    bones=source['bones']; weapon=source['weapon']; rest_rotation=FLIP@Rotation.from_quat(weapon['q']).as_matrix()@FLIP
    rest_point=FLIP@weapon['p']; grasps=[]
    for side in ['r','l']:
        shoulder,elbow,hand,knuckle=[FLIP@bones[n+'_'+side]['p'] for n in ('upperarm','lowerarm','hand','middle_01')]
        grasps.append((shoulder, np.linalg.norm(elbow-shoulder), np.linalg.norm(hand-elbow), rest_rotation.T@(hand-rest_point),rest_rotation.T@unit(knuckle-hand),rest_rotation.T@unit(hand-elbow),rest_rotation.T@unit(np.cross(elbow-shoulder,hand-elbow))))
    def unpack(x):
        x=x.reshape(N,14); p=x[:,:3]; rot=rotation_matrix(x[:,3:6]); hands=[]; palms=[]
        for side,(_,_,_,base,palm,_,_) in enumerate(grasps):
            twist=Rotation.from_rotvec(x[:,6+side,None]*np.array([0.,0.,1.])).as_matrix()
            grip=rot@twist; hands.append(grip@base+p); palms.append(grip@palm)
        return x,p,rot,hands,palms
    def loss(x):
        x,p,rot,hands,palms=unpack(x); z=rot[:,:,2]; across=rot[:,:,0]
        base=project(p); screen_tip=project(p+z*88); direction=unit(screen_tip-base)
        ref_tip=OBS[:,10:12]; ref_dir=unit(ref_tip-OBS[:,8:10]); tip_weight=OBS[:,12:13]
        guard_angle=np.deg2rad(OBS[:,13]); guard_dir=np.column_stack((np.cos(guard_angle),np.sin(guard_angle)))
        guard_proj=unit(project(p+across*4)-base)
        cross2=lambda a,b: a[:,0]*b[:,1]-a[:,1]*b[:,0]
        base_visible=((OBS[:,8]>1)&(OBS[:,8]<319)&(OBS[:,9]<178))[:,None]
        residual=[(base-OBS[:,8:10])*np.where(base_visible,.65,.19),
                  (direction-ref_dir)*np.clip(tip_weight,0,1)*20,
                  (screen_tip-ref_tip)*np.clip(tip_weight-1,0,1)*.48,
                  (cross2(guard_proj,guard_dir)*11)[:,None],
                  (x[:,3:5]-np.deg2rad(OBS[:,14:16]))*np.array([18,13]),
                  ((p[:,1]-36)*.16)[:,None], np.maximum(13-p[:,1],0)[:,None]*2,
                  x[:,6:8]*4.5, np.maximum(np.abs(x[:,6:8])-1.1,0)*32,
                  np.maximum(25-(p[:,1]-26.5*z[:,1]),0)[:,None]*4]
        pommel_frames=[1068,1071,1074,1077,1080,1083,1086]
        pommel_xy=np.array([[60,156],[94,125],[106,102],[112,78],[128,62],[145,49],[156,39]])
        pommel_target=PchipInterpolator(pommel_frames,pommel_xy,extrapolate=False)(FRAMES)
        residual.append(np.nan_to_num((project(p-z*26.5)-pommel_target))*.62)
        for side,(shoulder,upper,lower,_,_,old_forearm,old_hinge) in enumerate(grasps):
            hand=hands[side]; elbow=x[:,8+3*side:11+3*side]; hand_uv=OBS[:,2*side:2*side+2]; elbow_uv=OBS[:,4+2*side:6+2*side]
            visible=((elbow_uv[:,0]>3)&(elbow_uv[:,0]<317)&(elbow_uv[:,1]>2)&(elbow_uv[:,1]<176))[:,None]
            hand_visible=((hand_uv[:,0]>0)&(hand_uv[:,0]<320)&(hand_uv[:,1]<179))[:,None]
            observed_line=unit(elbow_uv-hand_uv); line=project(elbow)-project(hand)
            new_lower=unit(hand-elbow); hinge=unit(np.cross(elbow-shoulder,new_lower))
            rotation=rot@Rotation.from_rotvec(x[:,6+side,None]*np.array([0.,0.,1.])).as_matrix()
            forearm=rotation@old_forearm; palm_hinge=rotation@old_hinge
            swing=np.cross(forearm,new_lower); swing2=np.cross(swing,np.cross(swing,palm_hinge))
            palm_hinge=unit(palm_hinge+np.cross(swing,palm_hinge)+swing2/np.maximum(.001,1+(forearm*new_lower).sum(1)[:,None]))
            cosine=(hinge*palm_hinge).sum(1)
            # The two projective elbow solutions have very different diameters.
            # The close solution balloons into frame. Use the observed forearm width
            # and avoid axial roll beyond the usable range of the two twist stations.
            mid_depth=(hand[:,1]+elbow[:,1])*.5
            residual += [(project(hand)-hand_uv)*np.where(hand_visible,1.,.36),
                         (project(elbow)-elbow_uv)*np.where(visible,.86,.14),
                         (cross2(line,observed_line)*np.where(visible[:,0],.16,.75))[:,None],
                         ((np.linalg.norm(elbow-hand,axis=1)-lower)*7)[:,None],
                         ((np.linalg.norm(elbow-shoulder,axis=1)-upper)*.78)[:,None],
                         (unit(hand-elbow)-palms[side])*15,
                         (np.maximum(.77-np.sum(unit(hand-elbow)*palms[side],axis=1),0)*170)[:,None],
                         np.maximum(.18-cosine,0)[:,None]*60,
                         (1-cosine)[:,None]*5,
                         np.maximum(20-elbow[:,1],0)[:,None]*5,
                         np.maximum(23-hand[:,1],0)[:,None]*5,
                         np.maximum(28-mid_depth,0)[:,None]*3]
        per=np.concatenate(residual,axis=1)
        weights=np.array([.7,.9,.7,13,11,10,10,10,.65,.65,.65,.65,.65,.65])
        return np.r_[per.ravel(), (np.diff(x,axis=0)*weights*.53).ravel(), (np.diff(x,n=2,axis=0)*weights*2.3).ravel()]
    initial=np.zeros((N,14));initial[:,1]=38;initial[:,0]=(OBS[:,8]-160)*38/FOCAL;initial[:,2]=(90-OBS[:,9])*38/FOCAL
    initial[:,3:5]=np.deg2rad(OBS[:,14:16]);initial[:,5]=np.deg2rad(-65.)
    for s in range(2):
        depth=23.; uv=OBS[:,4+s*2:6+s*2];initial[:,8+s*3:11+s*3]=np.column_stack(((uv[:,0]-160)*depth/FOCAL,np.full(N,depth),(90-uv[:,1])*depth/FOCAL))
    count=loss(initial.ravel()).size; per=(count-14*(2*N-3))//N
    structure=lil_matrix((count,14*N),dtype=np.int8)
    for i in range(N):structure[per*i:per*(i+1),14*i:14*(i+1)]=1
    row=N*per
    for order in [1,2]:
        for i in range(N-order):
            for k in range(14):
                for j in range(order+1):structure[row+i*14+k,(i+j)*14+k]=1
        row+=14*(N-order)
    candidates=[]
    for neutral_roll in [-90,20,145,-200]:
        initial[:,5]=np.deg2rad(neutral_roll)
        answer=least_squares(loss,initial.ravel(),jac_sparsity=structure.tocsr(),x_scale='jac',max_nfev=180,ftol=2e-5)
        candidates.append(answer)
    solve=min(candidates,key=lambda candidate:candidate.cost)
    x,p,rot,hands,palms=unpack(solve.x); result=[]; stats={}
    for side,(shoulder,upper,lower,_,_,_,_) in enumerate(grasps):
        elbow=x[:,8+3*side:11+3*side];bend=np.rad2deg(np.arccos(np.clip(np.sum(unit(hands[side]-elbow)*palms[side],axis=1),-1,1))); err=np.linalg.norm(project(hands[side])-OBS[:,2*side:2*side+2],axis=1)
        stats['rl'[side]]=dict(wrist_px_median=round(float(np.median(err)),2),worst_px=round(float(max(err)),2),max_bend=round(float(max(bend)),1),roll_range=np.rad2deg([min(x[:,6+side]),max(x[:,6+side])]).round(1).tolist())
    for i in range(N):result.append(dict(frame=int(FRAMES[i]),p=p[i].tolist(),q=Rotation.from_matrix(rot[i]).as_quat().tolist(),spin=x[i,6:8].tolist(),elbows=x[i,8:].reshape(2,3).tolist(),heading=float(np.rad2deg(x[i,3]))))
    (HERE/(name+'-fit.json')).write_text(json.dumps(result,separators=(',',':')))
    print(name,solve.nfev,solve.cost,stats, flush=True)

if __name__=='__main__':
    (HERE/'screen-tracks.json').write_text(json.dumps(dict(first=int(FRAMES[0]),width=320,height=180,tracks=OBS.tolist()),separators=(',',':')))
    for grip in ['Standard','LongGrip']:fit(grip)
