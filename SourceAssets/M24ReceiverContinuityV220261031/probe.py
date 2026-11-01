import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend'),load_ui=False,use_scripts=False)
R={}
for ob in bpy.data.objects:
 if ob.type=='MESH' and any(n in ob.name.lower() for n in ('trigger','bolt','clip','base','scope')):
  p=np.array([v.co[:] for v in ob.data.vertices]);R[ob.name]={'bounds':[p.min(0).tolist(),p.max(0).tolist()],'matrix':list(map(list,ob.matrix_world)),'materials':[m.name if m else None for m in ob.data.materials]}
(O/'source_geometry.json').write_text(json.dumps(R,indent=2));print('M24_PARTS',json.dumps(R),flush=True)
