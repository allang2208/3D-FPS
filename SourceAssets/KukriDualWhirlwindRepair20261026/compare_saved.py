"""Compare the saved UE compressed poses to this repair's authored native poses."""
import importlib.util,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
OUT=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('author',OUT/'author.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
decoded=json.loads((OUT/'after-compressed.json').read_text());result={}
for label,data in a.base.rig.DATA.items():
    body=a.c.Body(data);authored=json.loads((OUT/(label+'-actions.json')).read_text());result[label]={}
    primary=[body.ix[k] for k in ('pelvis','spine_01','spine_03','spine_05')]+[body.ix[k+'_'+s] for s in 'lr' for k in ('clavicle','upperarm','lowerarm','hand','thigh','calf','foot','ball')]
    for role,clip in decoded[label]['clips'].items():
        local=np.asarray(authored['clips'][role]['frames']);p,q=body.world(local)
        actual=np.asarray(clip['world'])
        if len(actual)!=len(p):raise RuntimeError('Unexpected saved sample count '+label+' '+role)
        dp=np.linalg.norm(actual[:,:,:3]-p,axis=2)
        dq=(R.from_quat(q.reshape(-1,4)).inv()*R.from_quat(actual[:,:,3:7].reshape(-1,4))).magnitude().reshape(dp.shape)*180/np.pi
        row={'asset':clip['asset'],'frames':len(actual),'duration':clip['duration'],
             'all_bones_max_position_error_cm':float(dp.max()),'all_bones_max_rotation_error_degrees':float(dq.max()),
             'primary_max_position_error_cm':float(dp[:,primary].max()),'primary_max_rotation_error_degrees':float(dq[:,primary].max())}
        result[label][role]=row;print(label,role,json.dumps(row),flush=True)
(OUT/'saved-pose-comparison.json').write_text(json.dumps(result,indent=2))
