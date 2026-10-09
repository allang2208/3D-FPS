import json
from pathlib import Path
O=Path(__file__).parent
s={'__file__':str(O/'author_layout.py')}
exec(compile((O/'author_layout.py').read_text().split('best=None;choices=[]')[0],str(O/'author_layout.py'),'exec'),s)
print('BODY_WORLD',list(map(list,s['ob'].matrix_world)),flush=True)
print('RIG_WORLD',list(map(list,s['s']['rig'].matrix_world)),flush=True)
print('BODY_DIMS',list(s['ob'].dimensions),flush=True)
print('VERT_RANGE',[(min(v[j] for v in s['verts']),max(v[j] for v in s['verts'])) for j in range(3)],flush=True)
print('SELECTED',len(s['polys']),len(s['surface_ids']),flush=True)
print('MOUTH',list(s['s']['mouth']),flush=True)
p,h,t=s['s']['pose'](87,7,False)
m=p['WPN_root']@s['rest']['WPN_root'].inverted()
print('STOCK_CAM',[list(s['cam'](m@s['verts'][i])) for i in s['surface_ids'][::max(1,len(s['surface_ids'])//6)]],flush=True)
print('HAND_CAM',list(s['cam'](p['hand_l'].translation)),flush=True)
