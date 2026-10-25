"""Record native reversal correspondence and publish only the two Exit roles."""
import json,runpy
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/FurnitureRest20261022/ApartmentReverseExit20261024'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
data=read(OUT/'native_saved_samples.json');report={}
def error(a,b):
    a,b=np.asarray(a),np.asarray(b)
    return {'position_cm':float(np.linalg.norm(a[...,:3]-b[...,:3],axis=-1).max()),'rotation_degrees':float(np.degrees((R.from_quat(a[...,3:7].reshape(-1,4))*R.from_quat(b[...,3:7].reshape(-1,4)).inv()).magnitude()).max())}
for variant,spec in data.items():
    enter=np.asarray(spec['clips']['Rest.ApartmentBed.Enter']['world'])
    idle=np.asarray(spec['clips']['Rest.ApartmentBed.Idle']['world'])
    leave=np.asarray(spec['clips']['Rest.ApartmentBed.Exit']['world'])
    row={'reverse_frames':len(enter),'reverse_match':error(enter[::-1],leave[:len(enter)]),'idle_to_exit':error(idle[-1],leave[0]),'exit_to_stand':error(enter[0],leave[-1])}
    for key in ('reverse_match','idle_to_exit','exit_to_stand'):
        # Recompressing the reversed clip is lossy; permit sub-degree rotation
        # quantization while retaining the 0.5 mm positional correspondence.
        rotation_limit=.3 if key=='reverse_match' else .25
        if row[key]['position_cm']>.05 or row[key]['rotation_degrees']>rotation_limit:raise RuntimeError('Native reverse correspondence differs: '+variant+'/'+key)
    row['reverse_compression_tolerance']={'position_cm':.05,'rotation_degrees':.3}
    report[variant]=row
(OUT/'native_reverse_review.json').write_text(json.dumps(report,indent=2))
runpy.run_path(str(Path(__file__).with_name('publish_apartment_meshy_bed.py')),init_globals={'FURNITURE_REVISION':OUT.name,'CHANGED_CAMERAS_ONLY':True})
(OUT/'delivery.json').write_text(json.dumps({'revision':OUT.name,'native_save':read(OUT/'save_complete.json'),'saved_assets':read(OUT/'assets_saved.json'),'publication':read(OUT/'publication.json'),'reverse_review':report,'source_entry_seconds':3.3,'standing_hold_seconds':.1,'exit_seconds':3.4,'game_tested':False,'editor_started':False,'preview':str(OUT/'ReviewSaved/bed_exit.gif')},ensure_ascii=False,indent=2),encoding='utf-8')
print('NATIVE_REVERSE_EXIT_PUBLISHED',json.dumps(report))
