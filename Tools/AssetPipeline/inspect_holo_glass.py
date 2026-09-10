import bpy,json
from pathlib import Path
out=Path('D:/FPS3D/FPSGAME/SourceAssets/M4Holographic20260909')
bpy.ops.wm.open_mainfile(filepath=str(out/'M4_Holographic_Editable.blend'))
o=bpy.data.objects['SM_M4_Holographic'];rows=[]
for p in o.data.polygons:
 pts=[o.data.vertices[i].co for i in p.vertices];lo=[min(v[i] for v in pts) for i in range(3)];hi=[max(v[i] for v in pts) for i in range(3)]
 if hi[0]-lo[0]<.0002 and lo[2]>.038 and hi[2]<.067 and lo[1]>-.023 and hi[1]<.023:
  rows.append(dict(face=p.index,mat=p.material_index,lo=lo,hi=hi))
(out/'glass-faces.json').write_text(json.dumps(rows,indent=2))
import numpy as np
im=bpy.data.images.load('D:/FPS3D/FPSGAME/Content/holographicpacked.fbm/Holographic_low_Holosight_BaseColor.png');pix=np.array(im.pixels[:]).reshape(-1,4)
print('IMAGE_ALPHA',pix[:,3].min(),pix[:,3].max(),np.sum(pix[:,3]<.9))
