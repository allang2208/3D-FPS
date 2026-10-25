"""Measure actual native joint angles and wrist drift during planted support."""
import json
from pathlib import Path
import numpy as np

OUT=Path(__file__).resolve().parents[2]/'SourceAssets/FurnitureRest20261022/MeshyBedSupportedHands20261024'
data=json.loads((OUT/'native_saved_samples.json').read_text());report={}
def unit(v):return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-9)
for variant,spec in data.items():
    ix={n:i for i,n in enumerate(spec['names'])};frames=np.asarray(spec['clips']['Rest.Bed.Enter']['world']);positions=frames[...,:3];row={}
    for side,sign in [('l',1),('r',-1)]:
        point=lambda n:positions[:,ix[n+'_'+side]]
        upper,forearm=unit(point('lowerarm')-point('upperarm')),unit(point('hand')-point('lowerarm'))
        forward=unit(point('middle_01')-point('hand'));across=point('index_01')-point('pinky_01')
        across=unit(across-forward*(across*forward).sum(axis=1,keepdims=True));normal=np.cross(across,forward)*sign;across*=sign
        extension=np.degrees(np.arctan2((forearm*normal).sum(axis=1),(forearm*forward).sum(axis=1)))
        deviation=np.degrees(np.arcsin(np.clip((forearm*across).sum(axis=1),-1,1)))
        flex=np.degrees(np.arccos(np.clip((upper*forearm).sum(axis=1),-1,1)))
        support=point('hand')[round(4.7*30):round(6.6*30)+1]
        row[side]={'wrist_extension_degrees':[float(extension.min()),float(extension.max())],
                   'wrist_deviation_degrees':[float(deviation.min()),float(deviation.max())],
                   'elbow_flex_degrees':[float(flex.min()),float(flex.max())],
                   'planted_wrist_drift_cm':float(np.linalg.norm(support-support[0],axis=1).max())}
    report[variant]=row
(OUT/'native_ergonomics_review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
