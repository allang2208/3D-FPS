"""Compare actual saved Gunplay output against R4, including blended endpoints."""
from diagnose import O,R4,s,R
import json,numpy as np
old=json.loads((R4/'native-saved-glove.json').read_text());new=json.loads((O/'native-saved-glove.json').read_text());result=[]
for a,b in zip(old['families'],new['families']):
    ni=b['names'];oi=a['names'];oldrows={r['frame']:r for r in a['frames']};rows=[]
    fixed=[n for n in ni if n.endswith('_l') or n.startswith(('WPN_','hand_r')) or n.endswith('_r') and n.startswith(('thumb','index','middle','ring','pinky'))]
    for row in b['frames']:
        p=s.matrices(row['bones']);q=s.matrices(oldrows[row['frame']]['bones']);j=ni.index('hand_r');k=oi.index('hand_r')
        rows.append({'frame':row['frame'],'hand_position_cm':float(np.linalg.norm(p[j,:3,3]-q[k,:3,3])),
            'hand_rotation_degrees':float(np.degrees((R.from_matrix(s.rigid(p[j])[:3,:3])*R.from_matrix(s.rigid(q[k])[:3,:3]).inv()).magnitude())),
            'fixed_matrix_error':max(float(abs(p[ni.index(n)]-q[oi.index(n)]).max()) for n in fixed)})
    result.append({'family':b['family'],'hand_position_cm':max(r['hand_position_cm'] for r in rows),
        'hand_rotation_degrees':max(r['hand_rotation_degrees'] for r in rows),'fixed_matrix_error':max(r['fixed_matrix_error'] for r in rows)})
(O/'native-preservation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
assert all(r['hand_position_cm']<.001 and r['hand_rotation_degrees']<.001 for r in result)
