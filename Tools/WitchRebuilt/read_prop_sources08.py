import bpy,json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchMeshy20260919');result={}
for path in ('Delivery/CloudGripV02/SM_Witch_StaffGripV02.fbx','Authoring/LayeredV04/Preserved/Staff.fbx'):
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(root/path),use_anim=False)
 result[path]=[]
 for o in bpy.context.scene.objects:
  if o.type!='MESH':continue
  pts=[o.matrix_world@v.co for v in o.data.vertices];band=[p for p in pts if abs(p.z-.92)<.025]
  result[path].append({'name':o.name,'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)],'grip_points':[list(p) for p in band[:40]],'band_min':[min(p[i] for p in band) for i in range(3)] if band else [],'band_max':[max(p[i] for p in band) for i in range(3)] if band else []})
p=root.parent/'WitchRebuilt20260921/Revision08/prop_sources.json';p.write_text(json.dumps(result,indent=2));print(json.dumps(result))
