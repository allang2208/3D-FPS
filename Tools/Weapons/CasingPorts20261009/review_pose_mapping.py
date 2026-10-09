"""Requested port check, using saved mesh refs and compressed clip samples."""
import json
import numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation as R
O=Path(__file__).parent
D=json.loads((O/'ports_before.json').read_text())['weapons']
C=json.loads((O/'calibration.json').read_text())
G=json.loads((O/'geometry_report.json').read_text())
def position(t,v):return np.array(t['p'])+R.from_quat(t['q']).apply(np.array(v)*t['s'])
def inverse(t,p):return R.from_quat(t['q']).inv().apply(np.array(p)-t['p'])/t['s']
result={'kind':'saved mesh and compressed pose port mapping; no game run','weapons':{},'dual':{}}
for key,port in C.items():
 row=D[key];ref=row['mesh_reference'];anchor=port['anchor'];local=inverse(ref[anchor],position(ref['WPN_root'],np.array(port['root_cm'])*.01))
 clips={}
 for role,clip in row['clips'].items():
  samples=[]
  for s in clip['samples']:
   bones=s['bones'];world=position(bones[anchor],local)
   root_cm=inverse(bones['WPN_root'],world)*100
   samples.append({'time':s['time'],'root_cm':root_cm.tolist()})
  clips[role]=samples
 at_zero=clips['fire'][0]['root_cm']
 error=float(np.linalg.norm(np.array(at_zero)-port['root_cm']))
 if error>.001:raise RuntimeError(f'{key}: fire entry port changed by {error} cm')
 result['weapons'][key]={'anchor_local':local.tolist(),'fire_entry_reference_error_cm':error,'clips':clips,
  'position_delta_cm':float(np.linalg.norm(np.array(port['semantic_cm'])-port['old_semantic_cm']))}
 if anchor=='WPN_Slide':
  for side in ('r','l'):
   dual=D[key+'_'+side]['mesh_reference']
   local_dual=inverse(dual[anchor],position(dual['WPN_root'],np.array(port['root_cm'])*.01))
   back=inverse(dual['WPN_root'],position(dual[anchor],local_dual))*100
   result['dual'][key+'_'+side]={'anchor_local':local_dual.tolist(),'round_trip_error_cm':float(np.linalg.norm(back-port['root_cm']))}
result['revolvers']={'dw715':'Per-chamber WPN_Case bones use authored reload extraction; firing ejection disabled.',
 'rsh12':'Per-chamber extraction; dual reload release samples WPN_Case frames at release time, firing ejection disabled.'}
(O/'pose_mapping_review.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('Port pose mapping:',len(result['weapons']),'single automatic-ejection weapons,',len(result['dual']),'dual automatic-ejection meshes')
print('Max fire entry error cm:',max(v['fire_entry_reference_error_cm'] for v in result['weapons'].values()))
for key,v in result['weapons'].items():print(key,'position delta cm',round(v['position_delta_cm'],3))
