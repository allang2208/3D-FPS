"""Requested ALICE penetration diagnosis, using the exact captured old mount."""
import json,importlib.util
from pathlib import Path
import numpy as np
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BackpackMotion20261022'
spec=importlib.util.spec_from_file_location('alice_author',P/'Tools/BackpackMotion/author_alice.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
old=np.asarray(a.read(R/'alice_mount_before.json')['positions']);original=a.read(P/'SourceAssets/BackpacksReview20261021/alice_authored.json')
canvas=np.unique(np.asarray(original['triangles'])[np.asarray(original['triangle_materials'])==0]);old=old[canvas]
body=a.read(a.I/'body.json');source=a.read(R/'AliceFit/PreparedBag.json');rows=[]
for row in a.read(R/'AliceFit/manifest.json')['variants']:
    garment=a.read(a.I/(row['shirt']+'.json')) if row['shirt'] else None
    equations,_=a.envelope(body,garment);new=np.asarray(source['positions'])+row['bag_shift_cm']
    before=a.lift_required(old,np.tile([0.,-1.,0.],(len(old),1)),equations,.3)
    after=a.lift_required(new,np.tile([0.,-1.,0.],(len(new),1)),equations,.3)
    rows.append({'profile':row['profile'],'old_canvas_intruding_vertices':int((before>.001).sum()),'old_required_rear_clearance_cm':float(before.max()),
                 'fitted_required_rear_clearance_cm':float(after.max()),'fitted_pack_vertices':len(new)})
result={'cause':'old static transform shared with mountain bag, whole rigid shoulder loops and no garment-specific fit',
        'old_model_center_body_cm':[float(x) for x in (old.min(0)+old.max(0))/2],
        'scope':'reference-pose source geometry against visible native torso/garment envelope; no runtime pose or screenshot test',
        'profiles':rows,'runtime_tested':False}
(R/'alice_penetration_diagnosis.json').write_text(json.dumps(result,indent=2))
print(json.dumps(rows),flush=True)
