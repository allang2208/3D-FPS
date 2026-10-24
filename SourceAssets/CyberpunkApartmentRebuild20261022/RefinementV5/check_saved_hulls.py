"""Offline convex intersection using actual saved collision and component transforms."""
from pathlib import Path
import json,math
import numpy as np
from scipy.spatial import ConvexHull
from scipy.optimize import linprog
root=Path(__file__).resolve().parent
collision=json.loads((root/'saved-collision-hulls.json').read_text())
layout={a['label']:a for a in json.loads((root/'layout-after.json').read_text())}
rows=[]
hulls=[(r,np.asarray(r['vertices'],dtype=float)) for r in collision['hulls']]
def intersect(points,centre,half,rotation):
 p=(points-centre)@rotation
 if np.any(p.min(axis=0)>=half-.001) or np.any(p.max(axis=0)<=-half+.001):return False
 h=ConvexHull(p);eq=h.equations
 result=linprog(np.zeros(3),A_ub=eq[:,:3],b_ub=-eq[:,3]-.001,bounds=[(-x+.001,x-.001) for x in half],method='highs')
 if result.status not in (0,2):raise RuntimeError('Unresolved convex intersection '+str(result.message))
 return result.success
control=[r['actor'] for r,p in hulls if intersect(p,np.array([585.,-360.,144.]),np.array([2.,2.,2.]),np.eye(3))]
for label,a in sorted(layout.items()):
 if not label.startswith('Door_'):continue
 c=next(c for c in a['components'] if c['name']=='LeafLeft')
 b=np.asarray(c['bounds']);half=(b[1]-b[0])/2*np.array([1,.5,1]);scale=np.abs(a['scale'])
 # Unreal Rotator.to_tuple() exports pitch, roll, yaw.
 extent=np.maximum([1,1,1],half*scale-[2,2,4]);yaw=math.radians(a['rotation'][2]);co,si=math.cos(yaw),math.sin(yaw)
 R=np.array([[co,-si,0],[si,co,0],[0,0,1]])
 ends=[]
 for side in [-1,1]:
  centre=np.asarray(a['location'])+R@(np.array([0,side*(half[1]+a['slide_cm']),half[2]])*scale)
  blocked=[r['actor'] for r,p in hulls if intersect(p,centre,extent,R)]
  ends.append(dict(side=side,blocking_actors=sorted(set(blocked))))
 rows.append(dict(door=label,ends=ends))
report=dict(doors=rows,door_count=len(rows),blocked=[d['door'] for d in rows if any(e['blocking_actors'] for e in d['ends'])],
 collision_hulls_read=len(hulls),unhandled_collision_shapes=collision['other_shapes'],positive_control_actors=sorted(set(control)),
 valid='AP_Wall_Master' in control and not collision['other_shapes'],
 method='Saved collision convex hulls and boxes, complete component transforms, OBB/convex halfspace feasibility; known solid wall positive control',
 runtime_physics_queries_valid=False,game_run=False,rendered=False)
(root/'door-hull-clearance.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2))
