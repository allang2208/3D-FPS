"""Requested geometric review of actual rail contacts and native front-sight clearance."""
import json,numpy as np
from pathlib import Path
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;C=json.loads((O/'capture.json').read_text());a=np.load(O/'Working/host.npz');hp,ht,hm=a['p'],a['t'],a['m']
front=ht[(hm==C['host']['slots'].index('M_ASH12_Sights'))&(hp[ht][:,:,0].min(1)>.168)&(hp[ht][:,:,2].max(1)>0)]
host=BVHTree.FromPolygons(hp.tolist(),front.tolist());R={}
for key in ['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','eoth_holographic','thermal_scope']:
 a=np.load(O/f'Working/{key}.npz');p,t,m=a['p'].copy(),a['t'],a['m'];p[:,0]+=C['assets'][key]['along_m']
 excluded={i for i,s in enumerate(C['assets'][key]['slots']) if any(k in s['name'].lower() for k in ('glass','reticle','opticshoe'))}
 mask=~np.isin(m,list(excluded));tree=BVHTree.FromPolygons(p.tolist(),t[mask].tolist());overlap=host.overlap(tree)
 R[key]={'front_sight_triangle_intersections':len(overlap),'body_world_x_bounds_m':[float(p[:,0].min()),float(p[:,0].max())],'has_ash_contact_shoe':any(s['name']=='ASH_OpticShoe' for s in C['assets'][key]['slots'])}
 if key=='eoth_holographic':
  after=p.copy();after[:,0]-=.034
  R[key]['proposed_34mm_rear_shift_intersections']=len(host.overlap(BVHTree.FromPolygons(after.tolist(),t[mask].tolist())))
 print('ASH_CONTACT',key,R[key],flush=True)
(O/'contact_review.json').write_text(json.dumps(R,indent=2))
