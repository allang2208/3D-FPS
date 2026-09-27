"""Inspect the saved native poses using the accepted V7 bare-arms surface."""
import sys,json
from pathlib import Path
P=Path(__file__).parent;sys.path.insert(0,str(P))
from guard_source import *
setup_render();report={}
for variant in ('Standard','LongGrip'):
    data=json.loads((P/'After'/variant/'installed.json').read_text());report[variant]={}
    for clip in ('Guard','GuardHit','GuardBreak'):
        poses=[from_ue(s['world']) for s in data['clips'][clip]['samples']]
        rows=[metrics(p) for p in poses]
        report[variant][clip]={'max_wrist_bend_deg':max(r['wrist_bend_deg'] for r in rows),
            'max_elbow_seam_deg':max(abs(r['elbow_seam_deg']) for r in rows),'start':rows[0],'end':rows[-1]}
        if clip=='Guard':
            render_pose(poses[-1],P/'Review'/(variant+'_saved_fp.jpg'))
            render_pose(poses[-1],P/'Review'/(variant+'_saved_close.jpg'),True)
            report[variant]['held_blade_forward_dot']=(poses[-1]['Blade_Tip'].translation-poses[-1]['Blade_Base'].translation).normalized().y
        if clip=='GuardBreak' and variant=='Standard':
            for t in (.105,.25,.35):
                render_pose(poses[round(t*480)],P/'Review'/('Standard_saved_break_'+str(t)+'.jpg'))
(P/'saved_pose_inspection.json').write_text(json.dumps(report,indent=2))
print('GUARD_SAVED_POSE_REVIEW_COMPLETE',flush=True)
