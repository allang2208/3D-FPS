import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;src=json.loads((O/'source_frames.json').read_text());out={'arms':{},'rear':{}}
for family,info in src['arms'].items():
 b=info['bones'];p={n:Matrix(v['pose']) for n,v in b.items()};r={n:Matrix(v['rest']) for n,v in b.items()}
 S=p['upperarm_l'].translation;E=p['lowerarm_l'].translation;H=p['hand_l'];P=H.translation;L1=(E-S).length;L2=(P-E).length
 handaxis=(H.to_3x3()@r['hand_l'].to_3x3().inverted()@(r['hand_l'].translation-r['lowerarm_l'].translation)).normalized()
 W=p['WPN_root'].to_quaternion();best=None
 for x in [-.02,-.01,0,.01,.02]:
  for y in [-.03,-.02,-.01,0,.01,.02,.03]:
   for z in [-.02,-.01,0,.01,.02]:
    shift=W@Vector((x,y,z));s=S+shift;v=P-s;d=v.length
    if not abs(L1-L2)+.003<d<L1+L2-.006:continue
    n=v/d;a=(L1*L1-L2*L2+d*d)/(2*d);h=math.sqrt(max(0,L1*L1-a*a));C=s+n*a
    base=E-C;base=(base-n*base.dot(n)).normalized();ideal=P-handaxis*L2-C;ideal=(ideal-n*ideal.dot(n)).normalized()
    theta=math.atan2(n.dot(base.cross(ideal)),base.dot(ideal))
    for fraction in [.4,.55,.7,.85,1.]:
     e=C+Quaternion(n,theta*fraction)@base*h
     bend=math.degrees((P-e).angle(handaxis));move=(e-E).length
     loss=max(0,bend-18)**2+.025*move*move*1e6+.18*shift.length_squared*1e6
     if best is None or loss<best[0]:best=(loss,s,e,bend,shift,move)
 _,s,e,bend,shift,move=best
 out['arms'][family]={'shoulder':list(s),'elbow':list(e),'hand':list(P),'shift':list(shift),'shift_gun':list(W.inverted()@shift),'bend_deg':bend,'elbow_move_m':move,'before_bend_deg':info['bend_deg']}
 print('ARM',family,'bend',round(info['bend_deg'],2),'->',round(bend,2),'shoulder_mm', [round(c*1000,1) for c in (W.inverted()@shift)],'elbow_mm',round(move*1000,1),flush=True)
fit=Matrix(json.loads((O.parent/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
factory=[Vector(p) for ob in src['factory_grip'] for p in ob['vertices_gun']]
def bbox(v):return [[min(p[i] for p in v) for i in range(3)],[max(p[i] for p in v) for i in range(3)]]
print('FACTORY_GUN',bbox(factory))
for z in [-.11,-.09,-.07,-.05,-.03,-.01]:
 pts=[p for p in factory if abs(p.z-z)<.012]
 if pts:print('FACTORY_SECTION',z,bbox(pts))
xf=Matrix(json.loads((O.parent/'Accessories14/authoring.json').read_text())['rear_grip_transform'])
for key,obs in src['reargrips'].items():
 body=obs[0];v=[xf.inverted()@Vector(p) for p in body['vertices']]
 print('DONOR',key,'bounds',bbox(v))
 for mat,indices in body['material_vertices'].items():
  print('MAT',mat,bbox([v[i] for i in indices]))
out['factory_bounds']=bbox(factory)
(O/'fit_frames.json').write_text(json.dumps(out,indent=2))
