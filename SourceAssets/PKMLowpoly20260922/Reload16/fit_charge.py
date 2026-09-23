import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;s=json.loads((O/'sources.json').read_text());d=s['donor'];dr={n:Matrix(m) for n,m in d['rest'].items()};tips=json.loads((O.parent/'Bipod07/fingertips.json').read_text())
mesh=next(m for m in d['geometry'] if m['name']=='AKMR_Bolt_Native');pts=[dr['WPN_root'].inverted()@Vector(p) for p in mesh['points']]
print('DONOR_BOLT_ROOT_BOUNDS',[[min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]])
out={}
for f in ['54','66','75','84','96']:
 pose={n:Matrix(m) for n,m in d['poses'][f].items()};root=pose['WPN_root'];H=root.inverted()@pose['hand_r'];bolt=root.inverted()@pose['WPN_bolt']@dr['WPN_bolt'].inverted()@dr['WPN_root']
 # Locate the actual hooked finger pad at the donor handle; use the same
 # bone axes to transfer finger rotations, then refit the target PKM contact.
 point=root.inverted()@pose['index_02_r'].translation
 surf=min((bolt@p for p in pts),key=lambda p:(p-point).length_squared)
 print('CHARGE',f,'hand',list(H.translation),'index02',list(point),'nearest',list(surf),'gap', (surf-point).length)
 out[f]={'hand_root':[list(v) for v in H],'handle_point':list(surf),'anchor_hand':list(H.inverted()@surf),'hand_bolt':[list(v) for v in (root.inverted()@pose['WPN_bolt']).inverted()@H]}
(O/'charge_fit.json').write_text(json.dumps(out,indent=2))
