"""Save the repaired first-person master as editable Blender, FBX and GLB."""
import sys,bpy,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113'
sys.path.insert(0,str(S));import author_set as author
d=json.loads((S/'Integration/Delivery/gloves_M4_V7Master.json').read_text(encoding='utf-8'))
bpy.ops.wm.read_factory_settings(use_empty=True)
author.MATS=author.materials();author.OBJECTS=[];author.BONES=d['bones'];author.BONE_IDS={b['name']:b['index'] for b in d['bones']};author.RIG=author.rig_from(d['bones'])
d['authored_cloth_faces']=len(d['triangles'])
author.native_mesh('TS01_V7_ClosedGloves',d,{i:name.removeprefix('TS01_') for i,name in enumerate(d['material_slots'])})
author.save_part('FP_TacticalGloves_M4')
