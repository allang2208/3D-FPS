import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;L=u.EditorAssetLibrary;P='/Game/Weapons/AKMIntegration/SovietFab/GripErgonomic';path=P+'/BC_AKM_GripPrecision';settings=u.load_asset(path) if L.does_asset_exist(path) else L.duplicate_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel',path);codec=settings.get_editor_property('codecs')[0]
before={k:str(codec.get_editor_property(k)) for k in ['ErrorThreshold','DefaultVirtualVertexDistance','SafeVirtualVertexDistance','OptimizationTargets']};codec.set_editor_property('ErrorThreshold',.000001);codec.set_editor_property('OptimizationTargets',[u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/Attachments/SK_AKM_MannyNative')]);assert L.save_loaded_asset(settings,False)
for clip in ['idle','aim','fire','aim_fire','equip','reload','reload_empty','drum_reload','drum_reload_empty']:
 a=u.load_asset(P+'/angled/A_AKM_angled_'+clip);a.set_editor_property('bone_compression_settings',settings);u.AKMAnimationAuditLibrary.finish_animation_compression(a);assert L.save_loaded_asset(a,False)
(O/'compression_settings.json').write_text(json.dumps({'before':before,'asset':path,'ErrorThreshold':.000001,'optimization_target':'SK_AKM_MannyNative'},indent=2));u.log('GRIP_PRECISION_APPLIED')
