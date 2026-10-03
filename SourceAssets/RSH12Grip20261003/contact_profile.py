"""Private RSH contact corrections on shared native 715 animation poses."""
import json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;S=Matrix.Diagonal((1,-1,1,1))
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
def adapt(world,old,parents,kind,family,canonical,move_hand):
 ready='aim' if family=='single' and kind.startswith('aim') else 'idle'
 contract=json.loads((O/('hand_contact_'+family+'_'+ready+'.json')).read_text())
 changed=set();original={n:m.copy() for n,m in world.items()}
 for side,hand in contract['hands'].items():
  hn='hand_'+side;weight=1.
  if family=='single' and side=='l':
   distance=(canonical.inverted()@old[hn].translation-Vector(hand['hand_canonical'])).length
   weight=1-smooth((distance-.015)/.045)
  if weight<1e-5:continue
  delta=canonical.to_3x3()@Vector(hand['offset_canonical'])*weight
  changed.update(move_hand(world,original,side,delta))
  for n,value in hand['local_rotation_delta'].items():
   parent=parents[n];local=original[parent].inverted()@original[n];pos,q,scale=local.decompose()
   native=Quaternion((value[6],*value[3:6]));ue=(S@native.to_matrix().to_4x4()@S).to_quaternion()
   world[n]=world[parent]@Matrix.LocRotScale(pos,Quaternion().slerp(ue,weight)@q,scale);changed.add(n)
 return changed
