import bpy,json
from pathlib import Path
O=Path(__file__).parent;report={}
paths={'panoramic_red_dot':O.parent/'PanoramicRedDot20260911/GameIntegration/SM_PanoramicRedDot.fbx','lpvo_1_6x':O.parent/'LPVO1to6X20260911/SM_LPVO1to6X.fbx'}
for p in (O.parent/'PrismScope2X20260911').rglob('SM_PrismScope2X.fbx'):
 if 'Machined' in str(p):paths['prism_scope_2x']=p
for key,path in paths.items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(path));v=[o.matrix_world@v.co for o in bpy.context.scene.objects if o.type=='MESH' for v in o.data.vertices];low=[x for x in v if x.z<.003]
 report[key]={'source':str(path),'lo':[min(x[i] for x in v) for i in range(3)],'hi':[max(x[i] for x in v) for i in range(3)],'foot_lo':[min(x[i] for x in low) for i in range(3)],'foot_hi':[max(x[i] for x in low) for i in range(3)]}
(O/'bounds.json').write_text(json.dumps(report,indent=2));print('OPTIC_PROBE_PASS',report)
