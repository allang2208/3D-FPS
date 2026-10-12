from arm_core import *
cm=camera();rows={fam:posed('empty_7',fam) for fam in ('base',*D['profiles'])}
for clearance in (8,10,12,14):
 failures=[];summary=[];peak=0.
 for fam,ps in rows.items():
  for f in range(126,160):
   try:q=shoulder_under_frame(ps[f],f,clearance,cm)
   except ValueError:failures.append((fam,f));continue
   peak=max(peak,float(np.linalg.norm(q['upperarm_l'][:3,3]-ps[f]['upperarm_l'][:3,3])))
   if f in (132,136,140,144,148,152,156):
    m=measure(q,cm);summary.append([fam,f,m['cap_visible'],round(m['cap_penetration_cm'],2),round(m['nearest_upper_cm'] or 0,2)])
 print('SPHERE',clearance,'max_offset',round(peak,2),'failures',failures,'samples',summary,flush=True)
