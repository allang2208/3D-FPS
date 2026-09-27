"""Solve each original animation key so interpolated delta tracks do not shift the grip."""
import json,math,os,numpy as np
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';ns={}
exec((P/'Tools/ModularOutfit/probe_fingerless_shoulder_clearance.py').read_text().split('results=[]')[0],ns)
mx=ns['mx'];parents=ns['parents']
def matrix(k):return np.asarray(Matrix.LocRotScale(Vector(k['p']),Quaternion((k['q'][3],*k['q'][:3])),Vector(k['s'])))
def pack(m):return dict(position=m[:3,3].tolist(),axes=m[:3,:3].T.tolist())
for folder in ('CuffArmClearance','CuffShoulderClearance'):
    if os.environ.get('FINGERLESS_IK_FOLDER') and folder!=os.environ['FINGERLESS_IK_FOLDER']:continue
    root=R/folder;out=root/'NativeKeys';out.mkdir(exist_ok=True)
    for entry in json.loads((root/'manifest.json').read_text()):
        stem=entry['profile']+'__'+entry['label'];c=json.loads((root/(stem+'.json')).read_text());source=json.loads((root/'Before'/(stem+'_tracks.json')).read_text());times=np.asarray(c['times']);orbit=[]
        if folder=='CuffArmClearance':
            poses=json.loads((R/'ClearanceReview'/(stem+'_poses.json')).read_text())['poses'];co=c['corrections']['upperarm_r']
            for i,p in enumerate(poses):
                bones=p['bones'];u=mx(bones['upperarm_r']);el=mx(bones['lowerarm_r'])[:3,3];h=mx(bones['hand_r'])[:3,3];axis=h-u[:3,3];axis/=np.linalg.norm(axis);q=Quaternion(Vector(co['axes'][i]),math.radians(co['angles'][i]));new=u.copy();new[:3,:3]=u[:3,:3]@np.asarray(q.to_matrix());target=(new@np.linalg.inv(u)@np.r_[el,1])[:3];a=el-u[:3,3];a-=axis*(a@axis);b=target-u[:3,3];b-=axis*(b@axis);orbit.append(math.degrees(math.atan2(axis@np.cross(a,b),a@b)))
        after={bn:[] for bn in source['before']};hand_error=0.;translation_error=0.
        for i in range(source['keys']):
            time=source['duration']*i/max(1,source['keys']-1);world={};world['clavicle_r']=np.eye(4)
            for bn in ('clavicle_r','upperarm_r','lowerarm_r','hand_r'):
                if bn not in source['before']:continue
                parent=parents[bn];world[bn]=world.get(parent,np.eye(4))@matrix(source['before'][bn][i])
            bones={bn:pack(m) for bn,m in world.items()}
            if folder=='CuffArmClearance':
                clavicle=0.;elbow=float(np.interp(time,times,orbit));fade=min(1,abs(elbow)/2);fade=fade*fade*(3-2*fade);elbow+=math.copysign(2*fade,elbow)
            else:
                peaks=[]
                for index in (44,45):
                    t=max(0,1-abs(time-times[index])/.20);peaks.append(t*t*t*(10+t*(-15+6*t)))
                clavicle=max(30*peaks[0],5*peaks[1]);elbow=-60*max(peaks)
            solved=bones if abs(clavicle)+abs(elbow)<.00001 else ns['solve'](bones,[0,1,0],clavicle,elbow)
            if solved is None:raise RuntimeError('Unreachable '+stem+' key '+str(i))
            hand_error=max(hand_error,float(np.linalg.norm(mx(solved['hand_r'])-world['hand_r'])))
            for bn in after:
                parent=parents[bn];local=np.linalg.inv(mx(solved[parent]) if parent in solved else np.eye(4))@mx(solved[bn]);q=Matrix(local[:3,:3].tolist()).to_quaternion();k=dict(source['before'][bn][i]);translation_error=max(translation_error,float(np.linalg.norm(local[:3,3]-k['p'])));k['q']=[q.x,q.y,q.z,q.w];after[bn].append(k)
        if translation_error>.001:raise RuntimeError('Changed bone length '+stem+' '+str(translation_error))
        (out/(stem+'.json')).write_text(json.dumps(dict(asset=entry['asset'],keys=source['keys'],duration=source['duration'],tracks=after,hand_transform_error=hand_error,local_translation_error_cm=translation_error),separators=(',',':')));print('NATIVE_CUFF_KEYS',stem,source['keys'],hand_error,translation_error,flush=True)
