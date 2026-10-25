"""Inspect joint geometry and hand-support timing, rather than just penetration."""
import json,sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(sys.argv[sys.argv.index('--root')+1]) if '--root' in sys.argv else ROOT/'SourceAssets/FurnitureRest20261022/MeshyBedSideHands20261024'
ns={'__file__':str(ROOT/'Tools/FurnitureRest/meshy_bed.py')}
exec((ROOT/'Tools/FurnitureRest/meshy_bed.py').read_text().split('prefix=[]')[0],ns)
fk,ix,bind,unit=ns['fk'],ns['ix'],ns['bind'],ns['unit']
path=OUT/'ReviewSaved/saved_poses.json' if '--saved' in sys.argv else OUT/'authored.json'
data=json.loads(path.read_text());frames=np.asarray(data['clips']['Rest.Bed.Enter']['frames']);rows=[]
for j,f in enumerate(frames):
    w=fk(f);row={'time':j/30,'pelvis':w[ix['pelvis'],:3,3].tolist(),'hands':{}}
    chest=unit(w[ix['spine_05'],:3,3]-w[ix['pelvis'],:3,3]);row['torso_lean']=float(np.degrees(np.arctan2(-chest[1],chest[2])))
    for side,sign in [('l',1),('r',-1)]:
        a,b,c=[ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
        upper=unit(w[b,:3,3]-w[a,:3,3]);forearm=unit(w[c,:3,3]-w[b,:3,3])
        palm=w[c,:3,:3]@bind[c,:3,:3].T@ns['ns']['palm'][side]
        across,forward,normal=palm[:,0]*sign,palm[:,1],palm[:,2]*sign
        center=(w[c,:3,3]+w[ix['middle_01_'+side],:3,3])/2
        row['hands'][side]={'wrist':w[c,:3,3].tolist(),'palm_center':center.tolist(),
            'palm_center_surface_gap':float(center[2]-ns['surface'](*center[:2])),
            'elbow_flex_degrees':float(np.degrees(np.arccos(np.clip(upper@forearm,-1,1)))),
            'wrist_extension_degrees':float(np.degrees(np.arctan2(forearm@normal,forearm@forward))),
            'wrist_deviation_degrees':float(np.degrees(np.arcsin(np.clip(forearm@across,-1,1)))),
            'palm_up_dot':float(normal[2])}
    rows.append(row)
result={'source':str(path),'samples':rows,'extremes':{}}
for side in ('l','r'):
    result['extremes'][side]={}
    for field in ('elbow_flex_degrees','wrist_extension_degrees','wrist_deviation_degrees'):
        v=np.array([r['hands'][side][field] for r in rows]);k=int(abs(v).argmax())
        result['extremes'][side][field]={'min':float(v.min()),'max':float(v.max()),'extreme_time':k/30}
(OUT/('ergonomics_saved.json' if '--saved' in sys.argv else 'ergonomics.json')).write_text(json.dumps(result,indent=2))
print(json.dumps(result['extremes'],indent=2))
for t in (.8,1.5,2.8,3.5,4.,4.3,4.5,5.,5.5,6.,6.5,7.):
    row=rows[round(t*30)]
    print(t,'lean',round(row['torso_lean'],1),[(s,{k:np.round(v,1).tolist() for k,v in row['hands'][s].items() if k in ('wrist','palm_center_surface_gap','wrist_extension_degrees','wrist_deviation_degrees','palm_up_dot')}) for s in ('l','r')])
