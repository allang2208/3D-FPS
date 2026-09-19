import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4HK416Replica20260910/SK_M4_FoldingSights_HK416.fbx');r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');inv=(r.matrix_world@r.data.bones['WPN_root'].matrix_local).inverted();bpy.ops.import_scene.fbx(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4Drum20260909/SM_M4_LargeDrum.fbx');o=bpy.data.objects["SM_M4_LargeDrum"];pts=[inv@o.matrix_world@v.co for v in o.data.vertices];print('DRUM',[[min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]]);(O/'m4_root_inverse.json').write_text(json.dumps([list(v) for v in inv]));print('ROOT_PASS')

