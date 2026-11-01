"""Save the M24 V9 viewmodel and its private mechanical clips, without PIE."""
import json
from pathlib import Path
import unreal as u

O=Path('D:/FPS3D/FPSGAME/SourceAssets/M24CustomScope20261026')
ROOT='/Game/Weapons/M24/Gameplay20261026'
NATIVE='/Game/Weapons/M24/CustomScope20261026'
A=u.AssetToolsHelpers.get_asset_tools(); E=u.EditorAssetLibrary
source=json.loads((O/'gameplay_authoring.json').read_text())
receipt={'complete':False,'saved':[],'clips':{},'runtime_tested':False}
def save(asset):
    E.save_loaded_asset(asset,only_if_is_dirty=False)
    if asset.get_path_name() not in receipt['saved']:receipt['saved'].append(asset.get_path_name())
def load(file,folder,name,options):
    task=u.AssetImportTask(); task.filename=str(file); task.destination_path=folder
    task.destination_name=name; task.automated=True; task.replace_existing=True
    task.save=False; task.options=options
    A.import_asset_tasks([task])
    asset=u.load_asset(folder+'/'+name)
    if not asset:raise RuntimeError('Import did not create '+name)
    return asset
old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    options=u.FbxImportUI(); options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal=True; options.import_mesh=True; options.import_animations=False
    options.import_materials=False; options.import_textures=False; options.create_physics_asset=False
    options.skeletal_mesh_import_data.set_editor_property('import_morph_targets',True)
    options.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_COMPUTE_NORMALS
    mesh=load(source['mesh'],ROOT,'SK_M24_V9',options)
    slots=list(mesh.materials)
    for i,slot in enumerate(slots):
        key=str(slot.material_slot_name)
        path=('/Game/Characters/ModularOutfit20260924/BareSkinV9M4/MI_M4SkinV9'
              if key.startswith('MI_Manny') else NATIVE+'/Materials/M_'+key)
        material=u.load_asset(path)
        if not material:raise RuntimeError('Missing assigned material '+path)
        slot.material_interface=material; slots[i]=slot
    mesh.set_editor_property('materials',slots)
    receipt['arm_materials']=[i for i,slot in enumerate(slots) if str(slot.material_slot_name).startswith('MI_Manny')]
    sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
    settings=sub.get_lod_build_settings(mesh,0)
    settings.use_full_precision_u_vs=True; settings.recompute_normals=True; settings.recompute_tangents=True
    sub.set_lod_build_settings(mesh,0,settings)
    E.set_metadata_tag(mesh,'M24Source','DJMaesen + custom scope remix; see SourceAssets/M24CustomScope20261026/ATTRIBUTION.md')
    save(mesh); save(mesh.skeleton)
    receipt['mesh']=mesh.get_path_name(); receipt['skeleton']=mesh.skeleton.get_path_name()
    compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
    for role,row in source['clips'].items():
        options=u.FbxImportUI(); options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        options.import_mesh=False; options.import_animations=True; options.skeleton=mesh.skeleton
        options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        options.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
        clip=load(row['file'],ROOT+'/Animations','A_M24_'+role,options)
        if compression:clip.set_editor_property('bone_compression_settings',compression)
        save(clip); receipt['clips'][role]={'asset':clip.get_path_name(),'seconds':clip.get_play_length()}
    receipt['complete']=True
finally:
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
    (O/'gameplay_import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('M24_GAMEPLAY_ASSETS_SAVED',len(receipt['saved']),flush=True)
