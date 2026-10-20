from diagnose_grip import O,R6,s,camera_for_frame
import json,gzip,numpy as np,sys
mode=sys.argv[1] if len(sys.argv)>1 else 'candidate'
data={'frames':{},'triangles':{'bare':s.arms['triangles'],'glove':s.glove['triangles'],
    'coverage':[t for t,m in zip(s.coverage['triangles'],s.coverage['material_ids']) if m!=2],
    'gun':[t for t,m in zip(s.weapon['triangles'],s.weapon['material_ids']) if m>=2 and m not in (5,7)]},'camera_vertical_fov':75.}
fields=np.load(O.parent/'QuickMeleeHandR3_20261019/glove-correctives.npz')
surfaces={'bare':s.bare,'coverage':s.Surface(s.coverage,True),'gun':s.Surface(s.weapon),'glove':s.Surface(s.glove,extra={k:fields[k] for k in fields.files})}
for label,path in [('R6',R6/'native-saved-glove.json'),('R7',O/f'native-{mode}.json')]:
    f=json.loads(path.read_text())['families'][0];order=[f['names'].index(n) for n in s.names];camera=s.matrices([f['view_to_camera']])[0]
    for row in f['frames']:
        i=row['frame']
        if i not in [0,12,20,40,60,68,70,84,90]:continue
        p=s.matrices(np.array(row['bones'])[order]);view=camera_for_frame(camera,i)
        def transform(v):
            c=v@view[:3,:3].T+view[:3,3]
            return np.stack([c[...,1],10-c[...,0],c[...,2]+5],axis=-1).tolist()
        meshes={n:transform(surface.evaluate(p,row['morphs'])) for n,surface in surfaces.items()}
        meshes['bones']={n:transform(p[s.ids[n],:3,3]) for n in ['upperarm_r','lowerarm_r','hand_r','middle_03_r']}
        data['frames'].setdefault(str(i),{})[label]=meshes
with gzip.open(O/'review-action-meshes.json.gz','wt') as f:json.dump(data,f,separators=(',',':'))
print('R7_GRIP_REVIEW_PREPARED',mode,flush=True)
