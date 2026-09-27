import sys,json
from pathlib import Path
P=Path(__file__).parent;sys.path.insert(0,str(P))
from guard_source import *
data=json.loads((P/'Before/Standard/installed.json').read_text())
p=from_ue(data['clips']['Guard']['samples'][-1]['world'])
idle=from_ue(data['clips']['Idle']['samples'][0]['world'])
report={}
for n in ('clavicle_l','upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r','WPN_root','Blade_Base','Blade_Tip','index_01_l','index_02_l','index_03_l'):
    report[n]={'p':list(p[n].translation),'q':list(p[n].to_quaternion()),'s':list(p[n].to_scale()),'rest_p':list(rest[n].translation),'local_q':list((p[parents[n]].inverted()@p[n]).to_quaternion()),'idle_local_q':list((idle[parents[n]].inverted()@idle[n]).to_quaternion())}
report['axis']={n:list(p[n].to_quaternion()@rest[n].to_quaternion().inverted()@(rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized()) for n in ('hand_l','lowerarm_l')}
(P/'probe.json').write_text(json.dumps(report,indent=2))
