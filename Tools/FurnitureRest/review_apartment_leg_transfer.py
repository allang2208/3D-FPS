"""Record native knee trajectories and entry/exit seams for this requested review."""
import json,runpy
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/FurnitureRest20261022/ApartmentLegTransfer20261024R2'
runpy.run_path(str(Path(__file__).with_name('review_meshy_bed_saved.py')),init_globals={'FURNITURE_REVISION':OUT.name})
data=json.loads((OUT/'native_saved_samples.json').read_text());report={}
for variant,spec in data.items():
    ix={n:i for i,n in enumerate(spec['names'])};w=np.asarray(spec['clips']['Rest.ApartmentBed.Enter']['world']);row={}
    for side in ('l','r'):
        h,k,f=[w[:,ix[n+'_'+side],:3] for n in ('thigh','calf','foot')]
        a=k-h;b=f-k;la=np.linalg.norm(a,axis=1);lb=np.linalg.norm(b,axis=1)
        flex=np.degrees(np.arccos(np.clip((a*b).sum(axis=1)/(la*lb),-1,1)))
        transfer=flex[36:109]
        row[side]={'transfer_knee_flexion_degrees':[float(transfer.min()),float(transfer.max())],
                   'maximum_thigh_length_variation_cm':float(np.ptp(la)),
                   'maximum_calf_length_variation_cm':float(np.ptp(lb)),
                   'maximum_frame_foot_displacement_cm':float(np.linalg.norm(np.diff(f,axis=0),axis=1).max())}
    report[variant]=row
(OUT/'native_leg_review.json').write_text(json.dumps(report,indent=2))
print('NATIVE_LEG_TRAJECTORIES',json.dumps(report))
