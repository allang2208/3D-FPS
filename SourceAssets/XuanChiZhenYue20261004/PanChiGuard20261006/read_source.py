import bpy,json
import numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'BladeV3/XuanChi_BladeV3_Editable.blend'))
o=bpy.data.objects['SM_XuanChi_Guard_V3'];v=np.array([tuple(p.co) for p in o.data.vertices])
r={'object':o.name,'location':list(o.location),'rotation':list(o.rotation_euler),'scale':list(o.scale),'min':v.min(0).tolist(),'max':v.max(0).tolist(),'materials':[m.name for m in o.data.materials],'slices':[]}
for a,b in [(0,.02),(.02,.04),(.04,.06),(.06,.08),(.08,.10),(.10,.14)]:
    q=v[(abs(v[:,0])>=a)&(abs(v[:,0])<b)]
    if len(q):r['slices'].append({'abs_x':[a,b],'min':q.min(0).tolist(),'max':q.max(0).tolist(),'median':np.median(q,0).tolist()})
(P/'source_interface.json').write_text(json.dumps(r,indent=2))
print('PANCHI_FACTORY_INTERFACE '+json.dumps(r),flush=True)
