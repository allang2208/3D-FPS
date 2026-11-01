import bpy,bmesh,json,numpy as np
from pathlib import Path
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24StockContinuity20261031/M24_StockContinuity_Editable.blend'),load_ui=False,use_scripts=False)
ob=bpy.data.objects['M24_AdvancedFront_ForIndependentGrip'];bm=bmesh.new();bm.from_mesh(ob.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=0.0000005)
remaining=set(bm.verts);rows=[]
while remaining:
 todo=[remaining.pop()];group=[]
 while todo:
  v=todo.pop();group.append(v)
  for e in v.link_edges:
   w=e.other_vert(v)
   if w in remaining:remaining.remove(w);todo.append(w)
 p=np.array([v.co[:] for v in group]);rows.append({'vertices':len(group),'lo':p.min(0).tolist(),'hi':p.max(0).tolist()})
bm.free();(O/'components.json').write_text(json.dumps(sorted(rows,key=lambda r:r['lo'][1]),indent=2))
print('COMPONENTS',len(rows),flush=True)
for r in rows:
 if r['lo'][1]<.28:print(r,flush=True)
