"""Measure off-hinge knee rotation, chain lengths and frame continuity."""
import json,math,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/FurnitureRest20261022/BedSupportedV9'
if '--root' in sys.argv:OUT=Path(sys.argv[sys.argv.index('--root')+1])
ns={'__file__':str(ROOT/'Tools/FurnitureRest/bed_supported_v9.py')}
exec((ROOT/'Tools/FurnitureRest/bed_supported_v9.py').read_text().rsplit('for kind in kinds:',1)[0],ns)
fk,ix,reference,donor=[ns[k] for k in ('fk','ix','bind','donor_seat')]
saved='--saved' in sys.argv
sources={'previous':OUT.parent/'BedNaturalV8/authored.json','current':OUT/('ReviewSaved/saved_poses.json' if saved else 'authored.json')}
rows={}
for label,path in sources.items():
    rig=json.loads(path.read_text());report=[]
    for kind in sorted({k.split('.')[1] for k in rig['clips']}):
        maximum=step=length_error=0.;min_knee_space=999;last=None
        take=rig['clips'][f'Rest.{kind}.Enter'];frames=np.array(take['frames'])
        for f in frames:
            w=fk(f)
            for side in ('l','r'):
                a,b,c=[ix[n+'_'+side] for n in ('thigh','calf','foot')]
                upper=donor[b,:3,3]-donor[a,:3,3];lower=donor[c,:3,3]-donor[b,:3,3]
                axis=donor[a,:3,:3].T@np.cross(upper,lower);axis/=np.linalg.norm(axis)
                baseline=donor[a,:3,:3].T@donor[b,:3,:3]
                local=w[a,:3,:3].T@w[b,:3,:3]
                # A hinge rotation must leave its transverse axis unchanged.
                rotation=local@baseline.T;error=np.degrees(np.arccos(np.clip(axis@rotation@axis,-1,1)))
                maximum=max(maximum,float(error))
                for p,q in ((a,b),(b,c)):
                    length_error=max(length_error,abs(np.linalg.norm(w[p,:3,3]-w[q,:3,3])-np.linalg.norm(reference[p,:3,3]-reference[q,:3,3])))
                if last is not None:
                    for index in (a,b,c):step=max(step,float(np.degrees(R.from_matrix(last[index,:3,:3].T@w[index,:3,:3]).magnitude())))
            last=w
        report.append({'kind':kind,'maximum_knee_off_hinge_degrees':maximum,'maximum_bone_step_degrees':step,'bone_length_error_cm':length_error})
    rows[label]=report
    print(label,json.dumps(report),flush=True)
(OUT/('leg_hinges_saved.json' if saved else 'leg_hinges.json')).write_text(json.dumps(rows,indent=2))
assert all(r['maximum_knee_off_hinge_degrees']<.5 and r['bone_length_error_cm']<.01 for r in rows['current'])
