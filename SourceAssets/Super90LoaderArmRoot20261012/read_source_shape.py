from arm_core import *
cm=camera();result=dict(camera=cm.tolist(),cap_count=len(cap),branches={})
for role in ('normal_7','empty_7'):
 rows=posed(role);chosen={f:measure(rows[f],cm) for f in (0,80,88,96,104,110,116,120,125,130,138,144) if f<len(rows)}
 if role=='empty_7':chosen.update({f:measure(rows[f],cm) for f in (148,152,156,160)})
 result['branches'][role]=chosen
 print(role,json.dumps(chosen),flush=True)
(O/'source_shape.json').write_text(json.dumps(result,indent=2))
