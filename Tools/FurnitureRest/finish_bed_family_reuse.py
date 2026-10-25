"""Record per-bed native transitions and publish the complete fitted inventory."""
import json,runpy,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/FurnitureRest20261022'/globals().get('FURNITURE_REVISION','BedFamilyReuse20261024')
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
inventory=read(OUT/'inventory.json');native=read(OUT/'native_saved_samples.json');report={}
def error(a,b):
    a,b=np.asarray(a),np.asarray(b)
    return {'position_cm':float(np.linalg.norm(a[...,:3]-b[...,:3],axis=-1).max()),'rotation_degrees':float(np.degrees((R.from_quat(a[...,3:7].reshape(-1,4))*R.from_quat(b[...,3:7].reshape(-1,4)).inv()).magnitude()).max())}
for variant,spec in native.items():
    report[variant]={}
    for kind in inventory['types']:
        enter,idle,leave=[np.asarray(spec['clips'][f'Rest.{kind}.{phase}']['world']) for phase in ('Enter','Idle','Exit')]
        row={'enter_idle':error(enter[-1],idle[0]),'idle_exit':error(idle[-1],leave[0]),'exit_stand':error(leave[-1],enter[0]),'reverse':error(enter[::-1],leave[:len(enter)])}
        for key,value in row.items():
            if value['position_cm']>.05 or value['rotation_degrees']>(.5 if key=='reverse' else .3):raise RuntimeError(f'Native transition differs: {variant}/{kind}/{key}: {value}')
        report[variant][kind]=row
(OUT/'native_stage_review.json').write_text(json.dumps(report,indent=2))
if '--review-only' in sys.argv:
    print('BED_FAMILY_NATIVE_TRANSITIONS',json.dumps(report));raise SystemExit(0)
runpy.run_path(str(Path(__file__).with_name('publish_bed_family_reuse.py')),init_globals={'FURNITURE_REVISION':OUT.name})
result={'revision':OUT.name,'inventory':inventory,'fit_parameters':read(OUT/'fit_parameters.json'),'native_save':read(OUT/'save_complete.json'),'assets':read(OUT/'assets_saved.json'),'publication':read(OUT/'publication.json'),'native_transitions':report,
    'entry_animation_seconds':3.3,'alignment_seconds':.6,'nominal_entry_total_seconds':3.9,'exit_seconds':3.4,
    'male_geometry':read(OUT/'geometry_audit_saved.json'),'male_hand_body':read(OUT/'hand_body_contact_saved.json'),
    'review_scope':'Jason skin against 10 configured bed meshes; native Jason/Kaitlin transitions and camera tracks. No game, multiplayer or clothing-combination acceptance.',
    'game_tested':False,'editor_started':False,'git_commit':None,'git_push':None}
(OUT/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('BED_FAMILY_DELIVERED',len(inventory['types']),'types',sum(map(len,inventory['models'].values())),'models')
