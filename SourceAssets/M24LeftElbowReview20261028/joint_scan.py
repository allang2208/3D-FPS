from pathlib import Path
exec(compile((Path(__file__).parent/'review.py').read_text().split('setup_render();s.render.resolution_x=960')[0],'runtime','exec'))
def wrap(x):return (x+180)%360-180
def twist(q,axis):
 if q.w<0:q=-q
 return wrap(math.degrees(2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)))
def measure(row,side='l'):
 u,l,h=[x+'_'+side for x in ('upperarm','lowerarm','hand')]
 uq,lq,hq=[row[n].to_quaternion() for n in (u,l,h)]
 axis=rest[l].to_quaternion().inverted()@(rest[h].translation-rest[l].translation).normalized()
 ref=rest[u].to_quaternion().inverted()@rest[l].to_quaternion()
 hrel=rest[l].to_quaternion().inverted()@rest[h].to_quaternion()
 e=twist((uq@ref).inverted()@lq,axis);p=twist(lq.inverted()@hq@hrel.inverted(),axis)
 upper=row[l].translation-row[u].translation;lower=row[h].translation-row[l].translation
 result={'elbow_flex_deg':math.degrees(upper.angle(lower)),'elbow_axial_deg':e,'forearm_roll_deg':p,'reach_ratio':(row[h].translation-row[u].translation).length/(upper.length+lower.length),'upper_cm':upper.length*100,'lower_cm':lower.length*100}
 for j,share in ((1,1),(2,.5)):
  n=f'lowerarm_twist_{j:02d}_{side}';rel=rest[l].to_quaternion().inverted()@rest[n].to_quaternion()
  q=lq.inverted()@row[n].to_quaternion()@rel.inverted()
  result[f'twist{j}_error_deg']=abs(wrap(twist(q,axis)-p*share))
 return result
report={'source':ue.get('snapshot_origin'),'left':{},'source_shapes':[k.name for k in skin.data.shape_keys.key_blocks]}
rows=[]
for p in np.linspace(0,1,121):
 for ph in (0,.25,.5,.75):rows.append({'progress':float(p),'phase':ph,**measure(runtime(float(p),ph))})
for ph in np.linspace(0,1,121):rows.append({'progress':1,'phase':float(ph),**measure(runtime(1,float(ph)))})
report['sprint_samples']=rows
for role,data in ue['clips'].items():
 family='mag10' if role.endswith('_mag10') else 'base'
 measured=[measure(component(local_pose(role,i/data['fps'],family))) for i in range(data['keys'])]
 report['left'][role]={k:[min(v[k] for v in measured),max(v[k] for v in measured)] for k in measured[0]}
report['sprint_range']={k:[min(v[k] for v in rows),max(v[k] for v in rows)] for k in rows[0] if k not in ('progress','phase')}
(O/'joint_scan.json').write_text(json.dumps(report,indent=2))
print('JOINT_SCAN',json.dumps({'sprint':report['sprint_range'],'left_clips':report['left'],'shape_count':len(report['source_shapes'])}),flush=True)
