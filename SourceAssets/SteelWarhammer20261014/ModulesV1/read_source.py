import bpy,json
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'SprintDragV1/RigSource/SteelWarhammer_Editable.blend'))
o=bpy.data.objects['SM_SteelWarhammer'];frame=o.parent.data.bones['WPN_root'].matrix_local
points=np.array([tuple(frame.inverted()@v.co) for v in o.data.vertices])
rows=[]
for z in np.arange(-.16,1.,.025):
    band=points[(points[:,2]>=z)&(points[:,2]<z+.025)]
    if len(band):rows.append({'z':round(float(z),3),'min':band.min(0).tolist(),'max':band.max(0).tolist()})
data={'bounds':[points.min(0).tolist(),points.max(0).tolist()],'bands':rows}
(P/'source_dimensions.json').write_text(json.dumps(data,indent=2))
print(json.dumps(data))
