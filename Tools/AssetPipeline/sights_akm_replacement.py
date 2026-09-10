import bpy,json
from pathlib import Path
OUT=Path(r'D:\FPS3D\FPSGAME\SourceAssets\AKMReplacement')
bpy.ops.wm.open_mainfile(filepath=str(OUT/'akm_replacement_imported.blend'))
o=bpy.data.objects['high part akm'];components=json.loads((OUT/'akm_replacement_components.json').read_text())
for idx in [6,7,28,29]:
    pts=[o.matrix_world@o.data.vertices[i].co for i in components[idx]['ids']]
    print('SIGHT_COMPONENT',idx,'VERTICES',json.dumps([list(p)for p in pts]))
