import bpy,json
from pathlib import Path
p=Path(r'D:\FPS3D\FPSGAME\SourceAssets');r={}
for family in ['M4','AKM','QBZ191']:
 bpy.ops.wm.open_mainfile(filepath=str(p/'PhantomRearGripSeamFit20260913'/(family+'_Assembly_Editable.blend')))
 r[family]={}
 for o in bpy.context.scene.objects:
  if not o.name.startswith('Receiver_'):continue
  vs=[o.matrix_world@v.co for v in o.data.vertices]
  r[family][o.name]={'min':[min(v[i] for v in vs) for i in range(3)],'max':[max(v[i] for v in vs) for i in range(3)]}
(p/'TacticalDevices20260913/receiver_geometry.json').write_text(json.dumps(r,indent=2))
