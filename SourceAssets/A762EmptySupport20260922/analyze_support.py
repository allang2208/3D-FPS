"""Surface and anchor analysis of only the changed A762 support phase."""
from pathlib import Path
import json,numpy as np
O=Path(__file__).parent
exec(compile((O/'fit_support.py').read_text().split('solved=minimize')[0],str(O/'fit_support.py'),'exec'))
rows=json.loads((O/'source_pose_diagnosis.json').read_text())
target=np.array(json.loads((O/'fitted_support.json').read_text())['hand_in_root'])
report={}
for family,entry in rows.items():
    contacts={};drift=[]
    for frame,row in entry['poses'].items():
        p={n:np.array(m) for n,m in row.items()}
        skin=sum((bound[n]@p[n].T)[:,:3]*weights[:,i,None] for i,n in enumerate(names))
        minimum=float(shell.clearance(points(skin)[:,[0,2,1]]).min())
        contacts[frame]=minimum
        if 272<=int(frame)<=385:drift.append(float(np.linalg.norm(p['hand_l'][:3,3]-target[:3,3])*1000))
    report[family]={'minimum_body_envelope_clearance_mm_by_frame':contacts,
                    'support_hold_minimum_clearance_mm':min(v for f,v in contacts.items() if 272<=int(f)<=385),
                    'support_anchor_max_position_error_mm':max(drift),
                    'changes_outside_left_rotation_tracks':entry['changes_outside_left_rotation_tracks']}
    print('A762_SUPPORT_CONTACT',family,'hold_minimum_mm',report[family]['support_hold_minimum_clearance_mm'],'anchor_error_mm',max(drift),
          'other_track_changes',len(entry['changes_outside_left_rotation_tracks']),flush=True)
(O/'support_phase_diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
