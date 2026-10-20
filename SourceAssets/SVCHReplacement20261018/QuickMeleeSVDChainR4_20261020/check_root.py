"""Project actual open right-shoulder boundary vertices through the native camera."""
from pathlib import Path
import sys,json,numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'QuickMeleeHandR3_20261019'))
from check_surfaces import *
O=Path(__file__).resolve().parent;mode=sys.argv[1] if len(sys.argv)>1 else 'candidate'
T=bare.T;edges=np.sort(np.vstack([T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]]),axis=1)
edges,count=np.unique(edges,axis=0,return_counts=True);vi=bare.first[np.unique(edges[count==1])]
bn=np.array([names[j] for j in bare.weights.argmax(1)])
vi=np.array([j for j in vi if bn[j].startswith(('upperarm','clavicle')) and bn[j].endswith('_r')])
out=[];capture=json.loads((O.parent/'QuickMeleeHandR3_20261019/native-saved.json').read_text());poses=np.load(O/'poses.npz')
from action_framing import camera_for_frame
for family in capture['families']:
    cam=matrices([family['view_to_camera']])[0];tx=np.tan(np.radians(family['camera_horizontal_fov']/2));ty=tx/family['camera_aspect']
    order=[family['names'].index(n) for n in names]
    for row in family['frames']:
        fi=row['frame']
        if fi>=len(poses[family['family']]):continue
        q=poses[family['family']][fi];C=camera_for_frame(cam,fi);v=bare.evaluate(q)[vi];v=v@C[:3,:3].T+C[:3,3]
        visible=(v[:,0]>1)&(abs(v[:,1])<v[:,0]*tx)&(abs(v[:,2])<v[:,0]*ty)
        if visible.any():out.append({'family':family['family'],'frame':row['frame'],'visible_root_vertices':int(visible.sum())})
report={'mode':mode,'root_vertices':len(vi),'frames_with_visible_cut':out,'passed':not out}
(O/('root-frustum-'+mode+'.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report),flush=True)
if out:raise SystemExit(1)
