import unreal,json,runpy
from pathlib import Path
OUT=Path(r'D:\FPS3D\FPSGAME\SourceAssets\AKMReplacement')
DEST='/Game/Weapons/AKMReplacement'
mesh=unreal.load_asset(DEST+'/SK_AKM_Replacement')
slots=mesh.get_editor_property('materials');bindings_changed=False;usage_report=[]
for i,slot in enumerate(slots):
    original=slot.get_editor_property('material_interface').get_name().removesuffix('_PBR')
    mat=unreal.load_asset(DEST+'/'+original+'_PBR')
    assert mat,(i,original)
    # Local UE 5.8 MaterialEditingLibrary exposes SetMaterialUsage/HasMaterialUsage;
    # shader usage must be saved explicitly for cooked/game skeletal mesh draws.
    unreal.MaterialEditingLibrary.set_material_usage(mat,unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    unreal.MaterialEditingLibrary.recompile_material(mat)
    has_usage=unreal.MaterialEditingLibrary.has_material_usage(mat,unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    assert has_usage,('SkeletalMesh material usage missing',mat.get_path_name())
    saved=unreal.EditorAssetLibrary.save_loaded_asset(mat,only_if_is_dirty=False)
    assert saved,('PBR material save failed',mat.get_path_name())
    usage_report.append({'material':mat.get_path_name(),'skeletal_mesh_usage':has_usage,'saved':saved})
    if slot.get_editor_property('material_interface')!=mat:
        slot.set_editor_property('material_interface',mat);slots[i]=slot;bindings_changed=True
if bindings_changed:
    mesh.set_editor_property('materials',slots)
    saved=unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False)
    if not saved:raise RuntimeError('AKM replacement mesh save failed; close or update the owning editor asset before retrying')
assert len(usage_report)==7,usage_report
(OUT/'akm_replacement_material_usage.json').write_text(json.dumps({'passed':True,'materials':usage_report,'mesh_bindings_changed':bindings_changed},indent=2),encoding='utf-8')
unreal.log('AKM_REPLACEMENT_SKELETAL_MATERIAL_USAGE_OK '+json.dumps({'materials':len(usage_report),'all_usage_enabled':all(r['skeletal_mesh_usage']for r in usage_report),'all_saved':all(r['saved']for r in usage_report),'mesh_bindings_changed':bindings_changed}))
unreal.log('AKM_REPLACEMENT_MATERIAL_BINDINGS '+json.dumps([s.get_editor_property('material_interface').get_path_name()for s in mesh.get_editor_property('materials')]))
runpy.run_path(r'D:\FPS3D\FPSGAME\Tools\AssetPipeline\validate_akm_replacement_ue.py',init_globals={'AKMR_VALIDATION_CONTEXT':'Saved material overrides then validated loaded assets in the same process'})
