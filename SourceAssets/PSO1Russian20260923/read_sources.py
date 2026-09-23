"""Read the installed host materials/import inputs required to author PSO-1."""
import unreal as u, json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/PSO1Russian20260923')
L=u.MaterialEditingLibrary
result={'hosts':{},'textures':{},'a762_finish':{}}
paths={
 'AKM':'/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative',
 'A762':'/Game/Weapons/A762/Integrated20260920/SK_A762_Manny',
 'PKM':'/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular'}
for key,path in paths.items():
    mesh=u.load_asset(path)
    result['hosts'][key]={'mesh':mesh.get_path_name(),
      'source':list(mesh.get_editor_property('asset_import_data').extract_filenames()),
      'slots':{str(s.material_slot_name):s.material_interface.get_path_name() for s in mesh.materials}}
for key,path in {
 'AKM_BaseColor':'/Game/Weapons/AKMIntegration/SovietFab/ArmSupport/Textures/T_AKM_Mount_Base_color',
 'AKM_Metallic':'/Game/Weapons/AKMIntegration/SovietFab/ArmSupport/Textures/T_AKM_Mount_Metallic',
 'AKM_Roughness':'/Game/Weapons/AKMIntegration/SovietFab/ArmSupport/Textures/T_AKM_Mount_Roughness',
 'A762_Grain':'/Game/Weapons/A762/Refinement03/Textures/T_A762_RebuiltFinish',
 'PKM_BaseColor':'/Game/Weapons/PKMLowpoly20260922/OpticMount23/Textures/T_PKM23_Metal_BaseColor',
 'PKM_ORM':'/Game/Weapons/PKMLowpoly20260922/OpticMount23/Textures/T_PKM23_Metal_ORM',
}.items():
    tex=u.load_asset(path)
    result['textures'][key]={'asset':tex.get_path_name(),
      'source':list(tex.get_editor_property('asset_import_data').extract_filenames()),
      'srgb':tex.get_editor_property('srgb')}
mat=u.load_asset('/Game/Weapons/A762/Refinement03/Materials/M_A762_UpperReceiver03')
color=L.get_material_default_vector_parameter_value(mat,'FinishColor')
result['a762_finish']={'reference':mat.get_path_name(),'color':[color.r,color.g,color.b],
 'metallic':L.get_material_default_scalar_parameter_value(mat,'Metallic'),
 'roughness':L.get_material_default_scalar_parameter_value(mat,'RoughnessCenter')}
(O/'sources.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('PSO1_SOURCE_INPUTS_SAVED')
