"""Saved native frame-by-frame surfaces for the brief recovery excursion."""
from diagnose_recovery import O,R5,s,camera_for_frame
import json,gzip,numpy as np,sys
source=json.loads((R5/'native-saved-glove.json').read_text())['families'][0]
candidate=json.loads((O/'native-saved-glove.json').read_text())['families'][0] if (O/'native-saved-glove.json').exists() else None
data={'frames':{},'triangles':{'bare':s.arms['triangles'],
    'gun':[t for t,m in zip(s.weapon['triangles'],s.weapon['material_ids']) if m>=2 and m not in (5,7)]},'camera_vertical_fov':75.}
surfaces={'bare':s.bare,'gun':s.Surface(s.weapon)}
for label,f in [('R5',source),('R6',candidate)]:
    if not f:continue
    order=[f['names'].index(n) for n in s.names];camera=s.matrices([f['view_to_camera']])[0]
    for row in f['frames']:
        i=row['frame']
        if i not in [60,72,78,84,90,93,94,95,96,97,98,99,102,108]:continue
        p=s.matrices(np.array(row['bones'])[order]);view=camera_for_frame(camera,i)
        def transform(v):
            c=v@view[:3,:3].T+view[:3,3]
            return np.stack([c[...,1],c[...,0],c[...,2]],axis=-1).tolist()
        meshes={n:transform(surface.evaluate(p,row['morphs'])) for n,surface in surfaces.items()}
        meshes['bones']={n:transform(p[s.ids[n],:3,3]) for n in ['upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r']}
        data['frames'].setdefault(str(i),{})[label]=meshes
with gzip.open(O/'review-meshes.json.gz','wt') as f:json.dump(data,f,separators=(',',':'))
print('RECOVERY_SURFACES_PREPARED',flush=True)
