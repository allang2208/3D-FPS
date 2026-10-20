"""Compare the saved R4 with this elbow-only revision, using unchanged V9."""
from diagnose import O,R4,s
import sys,json,gzip,numpy as np
sys.path.insert(0,str(R4));from action_framing import camera_for_frame
source=np.load(R4/'poses.npz');candidate=np.load(O/'poses.npz')
capture=json.loads((R4/'native-saved-glove.json').read_text());family=capture['families'][0]
saved_capture=json.loads((O/'native-saved-glove.json').read_text()) if (O/'native-saved-glove.json').exists() else None
saved_family=saved_capture['families'][0] if saved_capture else None
saved_order=[saved_family['names'].index(n) for n in s.names] if saved_family else None
saved_rows={r['frame']:r for r in saved_family['frames']} if saved_family else {}
camera=s.matrices([family['view_to_camera']])[0]
data={'frames':{},'triangles':{'bare':s.arms['triangles'],'glove':s.glove['triangles'],
      'coverage':[t for t,m in zip(s.coverage['triangles'],s.coverage['material_ids']) if m!=2],
      'gun':[t for t,m in zip(s.weapon['triangles'],s.weapon['material_ids']) if m>=2 and m not in (5,7)]},
      'camera_vertical_fov':75.}
fields=np.load(O.parent/'QuickMeleeHandR3_20261019/glove-correctives.npz')
surfaces={'bare':s.bare,'coverage':s.Surface(s.coverage,True),'gun':s.Surface(s.weapon),
          'glove':s.Surface(s.glove,extra={k:fields[k] for k in fields.files})}
for i in [6,7,8,12,20,40,60,68,70,77,90]:
    view=camera_for_frame(camera,i)
    def transform(v):
        c=v@view[:3,:3].T+view[:3,3]
        return np.stack([c[...,1],10-c[...,0],c[...,2]+5],axis=-1).tolist()
    data['frames'][str(i)]={}
    for label,p in [('R4',source['base'][i]),('R5',candidate['base'][i])]:
        morphs=None
        if label=='R5' and saved_rows:
            p=s.matrices(np.array(saved_rows[i]['bones'])[saved_order]);morphs=saved_rows[i]['morphs']
        meshes={n:transform(surface.evaluate(p,morphs)) for n,surface in surfaces.items()}
        meshes['bones']={n:transform(p[s.ids[n],:3,3]) for n in ['upperarm_r','lowerarm_r','hand_r','middle_03_r']}
        data['frames'][str(i)][label]=meshes
with gzip.open(O/'review-action-meshes.json.gz','wt') as f:json.dump(data,f,separators=(',',':'))
print('R5_ELBOW_REVIEW_PREPARED')
