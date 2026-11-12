"""Continuity and finite output in the saved native animation graph captures."""
from pathlib import Path
import json,numpy as np,sys
from scipy.spatial.transform import Rotation as R
r=Path(__file__).resolve().parent;label=sys.argv[1] if len(sys.argv)>1 else 'final';root=r/('native_'+label)
g=json.loads((root/'box_normal_base/geometry.json').read_text());ix={n:i for i,n in enumerate(g['bones'])};report={};count=0
for folder in root.iterdir():
    if not folder.is_dir():continue
    meta=json.loads((folder/'review.json').read_text());a=np.fromfile(folder/'poses.f32',np.float32).reshape(-1,4+7*meta['bone_count']);count+=len(a);p=a[:,4:].reshape(len(a),meta['bone_count'],7)
    if not meta['complete'] or not np.isfinite(a).all():raise RuntimeError('Incomplete/nonfinite '+folder.name)
    end=np.flatnonzero(a[:,0]>=meta['duration'])[0];ids=[ix[n] for n in ['hand_l','lowerarm_l','upperarm_l']]
    boundary=np.linalg.norm(p[end,ids,:3]-p[end-1,ids,:3],axis=1)
    report[folder.name]=dict(complete=True,finite=True,frames=len(a),images=len(meta['frames']),end_boundary_cm=float(boundary.max()),duration=meta['duration'])
    if boundary.max()>.25:raise RuntimeError('Return discontinuity '+folder.name)
receipt=json.loads((root/'receipt.json').read_text())
if not receipt['complete'] or set(receipt['cases'])!=set(report):raise RuntimeError('Missing native cases')
(r/('native_'+label+'_review.json')).write_text(json.dumps(dict(cases=report,total_frames=count),indent=2))
print('NATIVE_REVIEW',len(report),count,'pose frames',sum(v['images'] for v in report.values()),'images; complete and finite; max end step cm',max(v['end_boundary_cm'] for v in report.values()))
