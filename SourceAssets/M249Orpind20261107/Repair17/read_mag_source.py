import bpy,json
from pathlib import Path
p=Path('D:/FPS3D/FPSGAME/SourceAssets');bpy.ops.wm.open_mainfile(filepath=str(p/'ExtMagRebuild20260919/M4_ExtMag_Editable.blend'),use_scripts=False)
o=bpy.data.objects['Factory_M4'];v=[o.matrix_world@v.co for v in o.data.vertices]
print('FACTORY_M4_GEOMETRY',len(v),[[min(p[k] for p in v),max(p[k] for p in v)] for k in range(3)],list(o.matrix_world));print('MATERIALS',[m.name for m in o.data.materials]);print('OTHERS',[(x.name,x.type) for x in bpy.data.objects if x.type=='ARMATURE'])
