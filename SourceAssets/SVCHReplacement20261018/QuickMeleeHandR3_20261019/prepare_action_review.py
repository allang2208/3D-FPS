"""Reconstruct saved V9 surfaces from actual Gunplay graph output and weights."""
from pathlib import Path
import sys,json,gzip
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from check_surfaces import *
O=HERE
from action_framing import camera_for_frame
candidate=sys.argv[1] if len(sys.argv)>1 else 'candidate'
fields=np.load(O/'glove-correctives.npz')
cover=Surface(coverage,True);gun=Surface(weapon)
blue_fixed=Surface(glove,extra={k:fields[k] for k in fields.files})
data={'frames':{},'triangles':{},'cameras':{},'source':'actual native Gunplay graph and runtime corrective weights'}
data['triangles']['coverage']=[t for t,m in zip(coverage['triangles'],coverage['material_ids']) if m!=2]
data['triangles']['bare']=arms['triangles'];data['triangles']['glove']=glove['triangles']
data['triangles']['gun']=[t for t,m in zip(weapon['triangles'],weapon['material_ids']) if m>=2 and m not in (5,7)]
frames={20,68}
for label,mode in [('R2','baseline'),('R3',candidate)]:
    capture=json.loads((O/('native-'+mode+'.json')).read_text())
    family=next(f for f in capture['families'] if f['family']=='base')
    order=[family['names'].index(n) for n in names]
    camera=matrices([family['view_to_camera']])[0]
    data['camera_vertical_fov']=float(np.degrees(2*np.arctan(np.tan(np.radians(family['camera_horizontal_fov'])/2)/family['camera_aspect'])))
    def camera_input(v):
        c=v@camera[:3,:3].T+camera[:3,3]
        return np.stack([c[...,1],10-c[...,0],c[...,2]+5],axis=-1)
    for row in family['frames']:
        fi=row['frame'];camera=camera_for_frame(matrices([family['view_to_camera']])[0],fi)
        if fi not in frames:continue
        p=matrices(np.array(row['bones'])[order]);morphs=row['morphs']
        surfaces={'coverage':cover.evaluate(p,morphs),'bare':bare.evaluate(p,morphs),
                  'glove':(blue_fixed if label=='R3' else blue).evaluate(p,morphs),'gun':gun.evaluate(p)}
        result={k:camera_input(v).tolist() for k,v in surfaces.items()}
        result['bones']={n:camera_input(p[ids[n],:3,3]).tolist() for n in ['upperarm_r','lowerarm_r','hand_r','middle_01_r','middle_03_r','index_metacarpal_r','pinky_metacarpal_r']}
        result['action_alpha']=row['action_alpha']
        data['frames'].setdefault(str(fi),{})[label]=result
with gzip.open(O/'review-action-meshes.json.gz','wt') as f:json.dump(data,f,separators=(',',':'))
print('Prepared native graph hand surfaces '+candidate,flush=True)
