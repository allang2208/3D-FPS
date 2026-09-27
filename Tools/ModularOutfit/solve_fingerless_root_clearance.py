"""Resolve residual folded finger roots with bounded anatomical joint rotations."""
import json,math,copy,os
from pathlib import Path
import numpy as np
from mathutils import Matrix
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';C=R/'FingerClearance';ns={}
exec((P/'Tools/ModularOutfit/check_fingerless_clearance.py').read_text().split('report=dict(')[0],ns)
def rot(axis,angle):
    x,y,z=axis;K=np.array([[0,-z,y],[z,0,-x],[-y,x,0]]);a=math.radians(angle);return np.eye(3)+math.sin(a)*K+(1-math.cos(a))*K@K
def setmatrix(bones,n,m):bones[n]=dict(position=m[:3,3].tolist(),axes=m[:3,:3].T.tolist())
reports=ns['read'](C/'corrected-check.json');manifest=ns['read'](C/'manifest.json');by_asset={v['asset']:v for v in manifest}
for row in reports:
    if row['worst']['depth_mm']<=.03:continue
    if os.environ.get('FINGERLESS_ROOT_LABEL') and row['label']!=os.environ['FINGERLESS_ROOT_LABEL']:continue
    name=row['profile'];label=row['label'];d=ns['read'](C/'CorrectedPoses'/(name+'__'+label+'_poses.json'));cpath=C/(name+'__'+label+'.json');c=ns['read'](cpath)
    sd=ns['read'](R/'SkinCoverage'/(name+'_review.json'));gd=ns['read'](R/'Authored'/(name+'.json'));s=ns['prepare'](sd,True);g=ns['prepare'](gd)
    fixes={};remaining=0.;max_angle=0.
    for i,p in enumerate(d['poses']):
        bones=p['bones'];original=copy.deepcopy(bones)
        for attempt in range(8):
            sp=ns['deform'](s,bones);gp=ns['deform'](g,bones);test=ns['measure'](s,g,sp,gp)
            if test['max_plane_cross_mm']<=.03:break
            a,b=test['worst_pair'];weights={}
            for v in s['t'][a]:
                for bn,w in sd['weights'][s['original_ids'][v]].items():weights[bn]=weights.get(bn,0)+w
            candidates=[bn for bn in weights if bn.startswith(('thumb_','index_','middle_','ring_','pinky_')) and '_metacarpal_' not in bn]
            if not candidates:break
            dominant=max(candidates,key=lambda n:weights[n]);parts=dominant.split('_');bn=parts[0]+'_01_'+parts[-1]
            related=[parts[0]+f'_{j:02d}_'+parts[-1] for j in (1,2,3)];bm=ns['matrix'](bones[bn]);tip=ns['matrix'](bones[related[1]])[:3,3]-bm[:3,3]
            face=gp[g['t'][b]];outward=-np.cross(face[1]-face[0],face[2]-face[0]);axis=np.linalg.inv(bm[:3,:3])@np.cross(tip,outward);axis/=max(np.linalg.norm(axis),1e-12)
            best=test['max_plane_cross_mm']+.1*math.sqrt(test['sum_squared_cross_mm']);choice=None
            directions=[axis]+[np.array([0.,math.cos(a),math.sin(a)]) for a in np.arange(0,2*math.pi,math.pi/4)]
            for axis,angle in [(a,n) for n in (4,8,12,18,24,30,36) for a in directions]:
                bnew=bm.copy();bnew[:3,:3]=bm[:3,:3]@rot(axis,angle);delta=bnew@np.linalg.inv(bm);trial=dict(bones)
                total=np.linalg.inv(ns['matrix'](original[bn])[:3,:3])@bnew[:3,:3];q=Matrix(total.tolist()).to_quaternion();qa=min(q.angle,2*math.pi-q.angle)
                if math.degrees(qa)>36.01:continue
                for child in related:setmatrix(trial,child,delta@ns['matrix'](bones[child]))
                scored=ns['measure'](s,g,ns['deform'](s,trial),ns['deform'](g,trial));score=scored['max_plane_cross_mm']+.1*math.sqrt(scored['sum_squared_cross_mm'])
                if score<best:best=score;choice=trial
                if scored['max_plane_cross_mm']<=.03:break
            if choice is None:break
            bones=choice
        result=ns['measure'](s,g,ns['deform'](s,bones),ns['deform'](g,bones));remaining=max(remaining,result['max_plane_cross_mm'])
        for bn in bones:
            if '_01_' not in bn or not bn.startswith(('thumb','index','middle','ring','pinky')):continue
            delta=np.linalg.inv(ns['matrix'](original[bn])[:3,:3])@ns['matrix'](bones[bn])[:3,:3];q=Matrix(delta.tolist()).to_quaternion()
            if q.w<0:q.negate()
            angle=math.degrees(q.angle)
            if angle<.001:continue
            max_angle=max(max_angle,angle)
            if bn not in fixes:fixes[bn]=dict(angles=[0.]*len(d['poses']),axes=[[0.,0.,1.] for _ in d['poses']],axis=[0.,0.,1.])
            fixes[bn]['angles'][i]=angle;fixes[bn]['axes'][i]=list(q.axis)
    for bn,v in fixes.items():
        times=np.asarray(c['times']);angles=np.asarray(v['angles']);env=angles.copy();ax=np.asarray(v['axes']).copy()
        for i,a in enumerate(angles):
            t=np.clip(1-abs(times-times[i])/.1,0,1);smooth=t*t*t*(10+t*(-15+6*t));replace=a*smooth>env;ax[replace]=v['axes'][i];env=np.maximum(env,a*smooth)
        v['angles']=env.tolist();v['axes']=ax.tolist()
    c['corrections']={k:v for k,v in c['corrections'].items() if '_01_' not in k};c['corrections'].update(fixes);c['remaining_sample_cross_mm']=remaining;c['max_angle']=max(c['max_angle'],max_angle);c['root_joint_correction']=list(fixes)
    cpath.write_text(json.dumps(c,indent=2));by_asset[c['asset']].update(remaining_sample_cross_mm=remaining,max_angle=c['max_angle'],root_joint_correction=list(fixes))
    print('FINGER_ROOT_CLEARANCE',label,round(remaining,5),list(fixes),round(max_angle,2),flush=True)
(C/'manifest.json').write_text(json.dumps(list(by_asset.values()),indent=2))
