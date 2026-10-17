"""Requested saved-animation readback: deformation and held cartridge contact."""
import json,gzip,numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation as R
O=Path(__file__).parent
saved=json.loads((O/'saved_animations.json').read_text());before=json.loads((O/'installed.json').read_text())
with gzip.open(O/'native_arms.json.gz','rt',encoding='utf-8') as f:skin=json.load(f)
rest=skin['rest'];rf=np.array(rest['hand_r'][:3])-rest['lowerarm_r'][:3]
def held(f):
 if f<18 or f>=360:return False
 index=0 if f<60 else min(6,1+(f-60)//50)
 return f<=44+index*50
result={}
for role,data in saved.items():
 old={r['frame']:r['world'] for r in before['clips'][role]['samples']['COMPRESSED']}
 samples=[];error=0.;angle=0.
 for row in data['samples']:
  p=row['world'];h=p['hand_r'];fore=np.array(h[:3])-p['lowerarm_r'][:3]
  natural=(R.from_quat(h[3:7])*R.from_quat(rest['hand_r'][3:7]).inv()).apply(rf)
  bend=np.degrees(np.arccos(np.clip(natural@fore/(np.linalg.norm(natural)*np.linalg.norm(fore)),-1,1)))
  samples.append({'frame':row['frame'],'wrist_bend_degrees':float(bend)})
  if held(row['frame']) and row['frame'] in old:
   b=old[row['frame']]['hand_r'];error=max(error,float(np.linalg.norm(np.array(h[:3])-b[:3])*10))
   angle=max(angle,float(np.degrees((R.from_quat(h[3:7])*R.from_quat(b[3:7]).inv()).magnitude())))
 result[role]={'length':data['length'],'source_hash_matches':data['source_hash']==data['expected_source_hash'],
  'held_hand_position_error_mm':error,'held_hand_rotation_error_degrees':angle,'samples':samples}
report={'scope':'Saved compressed asset poses only; no interactive game, audio or network run','clips':result}
(O/'saved_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:{n:v for n,v in row.items() if n!='samples'} for k,row in result.items()}))
