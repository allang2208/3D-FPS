"""UE drives rotation relative to reference in the parent bone's coordinate system."""
import math
import numpy as np
from pathlib import Path
import json
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonStrong20261117')
OUT=BASE/'R4_PoseRefined'
DRIVERS=[(f'R4_{form}_{s}',f'{bone}_{s}',axis,start,end)
         for s in ('l','r') for form,bone,axis,start,end in
         [('Shoulder','upperarm',1,28.,64.),('Biceps','lowerarm',2,11.,73.)]]

def pose_values(data,bind,posed):
    names={b['name']:b for b in data['bones']}
    values={}
    for name,bone,axis,start,end in DRIVERS:
        i=names[bone]['index'];parent=names[bone]['parent']
        ref=np.linalg.inv(bind[parent,:3,:3])@bind[i,:3,:3]
        local=np.linalg.inv(posed[parent,:3,:3])@posed[i,:3,:3]
        delta=local@np.linalg.inv(ref)
        theta=math.asin(float(np.clip(delta[2,0],-1,1))) if axis==1 else math.atan2(delta[1,0],delta[0,0])
        values[name]=float(np.clip((math.degrees(theta)-start)/(end-start),0.,1.))
    return values

def capture_reference_clips():
    # Both samples were captured from these exact project clips on Jason's original bone set.
    from scipy.spatial.transform import Rotation
    root=BASE.parent
    cfg=json.loads((root.parent/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    library=json.loads((root/'BackpackHarnessRebuild20261020/Inputs/poses.json').read_text())
    bones=json.loads((BASE/'R3_ArmsRefined/AnatomyReview/derived_saved_mesh.json').read_text())['bones']
    def matrix(values):
        t=np.eye(4);t[:3,:3]=Rotation.from_quat(values[3:7]).as_matrix()@np.diag(values[7:10]);t[:3,3]=values[:3];return t
    ref=np.array([matrix(library['reference'][b['name']]) for b in bones])
    bind=np.repeat(np.eye(4)[None,:,:],len(bones),axis=0)
    for i,b in enumerate(bones):bind[i,:3,:3]=np.array(b['axes']).T;bind[i,:3,3]=b['position']
    samples={}
    for key in ['Staff.FullBody.CastRelease','Rifle.Idle']:
        action=library['clips'][key];frame=action['frames'][0]
        if action['asset']!=cfg['clips'][key]:raise ValueError('Stale clip '+key)
        cs=np.array([matrix(frame['bones'][b['name']]) for b in bones])
        retarget=cs.copy()
        for i,b in enumerate(bones):
            parent=b['parent']
            if parent<0:continue
            local=np.linalg.solve(cs[parent],cs[i])
            local[:3,3]+=(np.linalg.solve(bind[parent],bind[i])-np.linalg.solve(ref[parent],ref[i]))[:3,3]
            retarget[i]=retarget[parent]@local
        samples[key]={'source':action['asset'],'time':frame['time'],'cs':retarget.tolist(),'drivers':pose_values({'bones':bones},bind,retarget)}
    (OUT/'Review/pose_samples.json').write_text(json.dumps(samples,separators=(',',':')))
    print({k:v['drivers'] for k,v in samples.items()})
if __name__=='__main__':capture_reference_clips()
