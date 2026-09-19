import bpy,json,sys
from pathlib import Path
O=Path(__file__).parent;S=O.parent;OLD=S/'AttachmentIconAudit20260914';sys.path.insert(0,str(OLD))
from icon_geometry import level_frame
jobs={'M4':('ue_m4a1','M4HK416Replica20260910/SK_M4_FoldingSights_HK416.fbx'),'AKM':('ue_akm','PhantomRearGripIntegration20260913/AKM/SK_AKM_MannyNative.fbx'),'QBZ':('ue_qbz191','PhantomRearGripIntegration20260913/QBZ191/SK_QBZ191_Manny.fbx')}
rows=[]
for gun,(weapon,file) in jobs.items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(S/file));rig=bpy.data.objects['SK_M4_Infima'];frame=level_frame(rig)
 rows.append({'key':weapon+'_magazine_ext_mag','gun':gun,'source':str(S/'ExtMagContinuity20260919'/(gun+'_ExtMag_Continuous_Editable.blend')),'objects':['SM_ExtMag_'+gun+'40_Continuous'],'frame':'measured','matrix':list(map(list,frame)),'frame_source':str(S/file),'runtime':'/Game/Weapons/ExtMagContinuity20260919/SM_ExtMag_'+gun+'40_Continuous'})
(O/'render_manifest.json').write_text(json.dumps({'renders':rows},indent=2))
# Reuse the accepted icon studio without rewriting its historical manifest.
code=(OLD/'render_icons.py').read_text()
code=code.replace("sys.path.insert(0,str(P))","sys.path.insert(0,str(P.parent/'AttachmentIconAudit20260914'));sys.path.insert(0,str(P))")
code=code.replace('from icon_materials import restore_runtime_finish','from materials import restore_runtime_finish')
code=code.replace("def frame_for(row):","def frame_for(row):\n if row['frame']=='measured':return Matrix(row['matrix'])")
(O/'render.py').write_text(code)
