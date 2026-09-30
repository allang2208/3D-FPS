"""Shared authoring coordinates for the 201 game-art belt conversion."""
import json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent
FEED=Vector((.0008,-.175,.056))
HINGE=Vector((.0008,-.232,.0698))
SCALE=.8
def ue(v):
 p=v['p'];x,y,z,w=v['q']
 return Matrix.LocRotScale(Vector((p[0],-p[1],p[2]))*.01,Quaternion((w,-x,y,-z)),Vector(v['s'])*.01)
def load_donor():
 d=json.loads((O/'pkm_installed_donor.json').read_text())
 return d,{n:ue(v) for n,v in d['bones'].items()},[{n:ue(v) for n,v in row.items()} for row in d['clips']['idle']['poses']][0]
def local_pose(row):
 p={n:ue(v) for n,v in row.items()};root=p['WPN_root'];return root,{n:root.inverted()@m for n,m in p.items()}
def canonical(n):return n.removeprefix('New_')
def mapped_name(n):return n.replace('PKM_','LMG201_')
def mechanical(n):
 n=canonical(n)
 return n in ('PKM_Box','PKM_BoxLid','PKM_BeltRoot') or n.startswith(('PKM_Belt_','PKM_EmptyLink'))
def map_point(v,origin):return FEED+(v-origin)*SCALE
def map_frame(m,origin):
 result=Matrix.LocRotScale(map_point(m.translation,origin),m.to_quaternion(),Vector((1,1,1)))
 return result
def smooth(v):
 v=max(0.,min(1.,v));return v*v*v*(v*(v*6.-15.)+10.)
def ramp(t,a,b):return smooth((t-a)/(b-a))
def profile(t,keys):
 if t<=keys[0][0]:return keys[0][1]
 for (a,x),(b,y) in zip(keys,keys[1:]):
  if t<=b:return x+(y-x)*ramp(t,a,b)
 return keys[-1][1]
def assign(r,a):
 r.animation_data_create();r.animation_data.action=a
 if a.slots:r.animation_data.action_slot=a.slots[0]
