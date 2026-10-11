from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'arm_clearance.py').read_text(encoding='utf-8'),str(O/'arm_clearance.py'),'exec'))
for off in ((0,-8,-6),(3,-16,-14),(6,-20,-14),(6,-16,-18),(9,-20,-18)):
    invalid=[];metrics=[]
    for branch in ('normal','empty'):
        rows=source_rows[branch];end=len(rows)-1
        for f in range(89,end):
            p=rows[f];w=envelope(f,end)
            try:q=support_pose(p,off,0,w)
            except ValueError:invalid.append((branch,f));continue
            if f in (108,114,120,125,138,150):metrics.append((branch,f,round(clearance_cost(q),2),coverage(cloth_points(q),proximal)))
    print('OFFSET',off,'invalid',invalid,'metrics',json.dumps(metrics),flush=True)
