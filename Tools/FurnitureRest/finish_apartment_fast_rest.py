"""Publish the saved native clocks and retain the requested transition review."""
import json,runpy
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/FurnitureRest20261022/ApartmentFastRest20261024R2'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
native=read(OUT/'native_saved_samples.json');report={}
def error(a,b):
    a,b=np.asarray(a),np.asarray(b)
    return {'position_cm':float(np.linalg.norm(a[...,:3]-b[...,:3],axis=-1).max()),'rotation_degrees':float(np.degrees((R.from_quat(a[...,3:7])*R.from_quat(b[...,3:7]).inv()).magnitude()).max())}
for name,spec in native.items():
    clips={r.split('.')[-1]:np.asarray(v['world']) for r,v in spec['clips'].items()};enter,idle,leave=(clips[p] for p in ('Enter','Idle','Exit'))
    joins={'enter_idle':error(enter[-1],idle[0]),'idle_exit':error(idle[-1],leave[0]),'exit_stand':error(leave[-1],enter[0])}
    if any(v['position_cm']>.05 or v['rotation_degrees']>.25 for v in joins.values()):raise RuntimeError('Native transition seam: '+name)
    report[name]=joins
(OUT/'native_stage_review.json').write_text(json.dumps(report,indent=2))
runpy.run_path(str(Path(__file__).with_name('publish_apartment_fast_rest.py')))
result={'revision':OUT.name,'native_save':read(OUT/'save_complete.json'),'saved_assets':read(OUT/'assets_saved.json'),'publication':read(OUT/'publication.json'),
    'entry_animation_seconds':3.3,'existing_alignment_seconds':.6,'nominal_entry_total_seconds':3.9,'exit_seconds':3.9,
    'pacing':'Smooth monotone source clock, zero endpoint velocity, shortened preparation/recline, native male and female contact poses retained.',
    'stage_joins':report,'male_geometry':read(OUT/'geometry_audit_saved.json'),'male_hand_body':read(OUT/'hand_body_contact_saved.json'),
    'preview':str(OUT/'ReviewSaved/bed_entry.gif'),'game_tested':False,'editor_started':False,'existing_play_ended_to_save_assets':True,'git_commit':None,'git_push':None}
(OUT/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('FAST_REST_DELIVERED',result['nominal_entry_total_seconds'],result['exit_seconds'])
