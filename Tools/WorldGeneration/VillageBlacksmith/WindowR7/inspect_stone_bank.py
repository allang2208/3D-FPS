import bpy,json
from pathlib import Path
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/HillsVillageBlacksmith20261117/MasonryR5/HouseStoneBank.blend')
bank=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.location.y>.02 and o.dimensions.x>.25 and o.dimensions.z>.16]
print('BANK',len(bank))
for o in bank[:4]:
 p=[v.co for v in o.data.vertices];lo=Vector([min(v[i] for v in p) for i in range(3)]);hi=Vector([max(v[i] for v in p) for i in range(3)])
 print(o.name,'dims',list(o.dimensions),'origin',list(o.location),'scale',list(o.scale),'center',list((lo+hi)/2),'verts',len(p))
