from pathlib import Path
import sys,json,gzip
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'QuickMeleeSVDReferenceR2_20261019'))
from surface import *
O=HERE
sys.path.insert(0,str(O))
from check_surfaces import Surface
fields=np.load(O/'glove-correctives.npz') if (O/'glove-correctives.npz').exists() else None
glove_candidate=Surface(glove,extra={k:fields[k] for k in fields.files} if fields is not None else None)
poses=np.load(O/'poses.npz')
data={'frames':{},'triangles':{},'cameras':{}}
data['triangles']['coverage']=[t for t,m in zip(coverage['triangles'],coverage['material_ids']) if m!=2]
data['triangles']['bare']=arms['triangles'];data['triangles']['glove']=glove['triangles']
data['triangles']['gun']=[t for t,m in zip(weapon['triangles'],weapon['material_ids']) if m>=2 and m not in (5,7)]
for frame in (0,6,12,20,40,64,68,75,90,100,108):
    row={}
    for name,key in [('R2','before'),('R3','base')]:
        p=poses[key][frame]
        row[name]={k:skinned(src,p,k in ('coverage','bare')).tolist() for k,src in [('coverage',coverage),('bare',arms),('glove',glove),('gun',weapon)]}
        if name=='R3':row[name]['glove']=glove_candidate.evaluate(p).tolist()
        row[name]['bones']={n:p[ids[n],:3,3].tolist() for n in ['hand_r','middle_01_r','middle_03_r','index_metacarpal_r','pinky_metacarpal_r']}
    data['frames'][str(frame)]=row
with gzip.open(O/'review-meshes.json.gz','wt') as f:json.dump(data,f,separators=(',',':'))
print('Prepared hand, finger and wrist surfaces',flush=True)
