import sys,json
from pathlib import Path
P=Path(__file__).parent;sys.path.insert(0,str(P))
from guard_source import *
setup_render();out=P/'Review';out.mkdir(exist_ok=True)
report={}
for variant in ('Standard','LongGrip'):
    data=json.loads((P/'Before'/variant/'installed.json').read_text())
    report[variant]={}
    for clip,info in data['clips'].items():
        values=[metrics(from_ue(r['world'])) for r in info['samples']]
        report[variant][clip]={'frames':len(values),'seconds':info['seconds'],
            'start':values[0],'end':values[-1],
            'max_wrist_bend_deg':max(r['wrist_bend_deg'] for r in values),
            'max_elbow_seam_deg':max(abs(r['elbow_seam_deg']) for r in values)}
    held=from_ue(data['clips']['Guard']['samples'][-1]['world'])
    render_pose(held,out/(variant+'_before_fp.jpg'))
    render_pose(held,out/(variant+'_before_close.jpg'),True)
(P/'diagnosis.json').write_text(json.dumps(report,indent=2))
print('GUARD_DIAGNOSIS_COMPLETE',flush=True)
