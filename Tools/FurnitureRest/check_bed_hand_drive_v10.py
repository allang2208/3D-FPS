"""Measure fixed bed contacts and the elbow effort in the authored/saved motion."""
import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/FurnitureRest20261022/BedHandDriveV10'
ns={'__file__':str(ROOT/'Tools/FurnitureRest/bed_supported_v9.py')}
exec((ROOT/'Tools/FurnitureRest/bed_supported_v9.py').read_text().rsplit('for kind in kinds:',1)[0],ns)
fk,ix=ns['fk'],ns['ix'];saved='--saved' in sys.argv
rig=json.loads((OUT/('ReviewSaved/saved_poses.json' if saved else 'authored.json')).read_text())
choreography=json.loads((OUT/'choreography.json').read_text());rows=[]
direct=json.loads((OUT/'contact_samples.json').read_text()) if saved else None
for kind,design in choreography.items():
    take=rig['clips'][f'Rest.{kind}.Enter'];frames=np.array(take['frames']);rate=(len(frames)-1)/take['duration']
    errors=[];angles={s:[] for s in ('l','r')}
    if direct:
        assert direct[kind]['asset']==take['asset']
        measured={round(r['t'],6):r['bones'] for r in direct[kind]['samples']}
    for row in design['frames']:
        f=ns['sample'](frames,row['t']*rate/30);w=fk(f)
        for side,contact in row['contacts'].items():
            if not contact['planted']:continue
            a,b,c=([np.array(measured[round(row['t'],6)][side][n]) for n in ('upperarm','lowerarm','hand')] if direct else [w[ix[n+'_'+side],:3,3] for n in ('upperarm','lowerarm','hand')])
            errors.append(float(np.linalg.norm(c-contact['target'])))
            u=b-a;v=c-b;angle=np.degrees(np.arccos(np.clip(u@v/np.linalg.norm(u)/np.linalg.norm(v),-1,1)))
            angles[side].append(float(angle))
    rows.append({'kind':kind,'pushes':design['pushes'],'sampling':'direct UE compressed contact times at 30 Hz' if direct else 'authored 30 Hz','maximum_fixed_palm_error_cm':max(errors,default=0),
                 'support_elbow_flexion_degrees':{s:[min(v),max(v)] for s,v in angles.items() if v}})
    print(json.dumps(rows[-1]),flush=True)
(OUT/('hand_drive_saved.json' if saved else 'hand_drive.json')).write_text(json.dumps(rows,indent=2))
assert all(r['maximum_fixed_palm_error_cm']<.4 for r in rows), 'A supporting palm is sliding or out of reach'
