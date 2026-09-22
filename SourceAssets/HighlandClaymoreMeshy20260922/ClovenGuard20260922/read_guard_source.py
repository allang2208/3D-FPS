import bpy,json
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'Integration/HighlandClaymore_Modular_Editable.blend'))
m=bpy.data.objects['SM_Highland_Guard_factory'].data
p=np.array([tuple(v.co) for v in m.vertices]);rows=[]
for x in np.arange(.045,.225,.01):
    q=p[(np.abs(p[:,0])>=x)&(np.abs(p[:,0])<x+.01)]
    if len(q):rows.append({'x':round(float(x),4),'y':[float(q[:,1].min()),float(q[:,1].max())],'z':[float(q[:,2].min()),float(q[:,2].max())]})
r={'bounds_m':[p.min(0).tolist(),p.max(0).tolist()],'sections':rows,'materials':[v.name for v in m.materials]}
(P/'source_guard.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print('GUARD_SOURCE '+json.dumps(r))
