"""Author V05 UE packages from the preserved original robe and hidden cloth cage."""
import json,sys
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchMeshy20260919')
OUT=ROOT/'Authoring/OriginalRobeV05'
BASE='/Game/Monsters/WitchMeshy'
DEST=BASE+'/OriginalRobeV05'
LIB=u.EditorAssetLibrary
AT=u.AssetToolsHelpers.get_asset_tools()
ROLES=['Idle','Walk','CastPoison','ThrowPoisonBottle','DeathBackward']
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/Witch')
from repair_v05_cloth_binding import repair_original_robe_cloth
REPORT=ROOT/'ue_original_robe_v05.json'
report=json.loads(REPORT.read_text(encoding='utf-8')) if REPORT.exists() else {'revision':'OriginalRobeV05','completed':[],'runtime_tested':False}

def record(message):
    if message not in report['completed']:report['completed'].append(message)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

def save(asset):
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())

def duplicate(source,destination):
    asset=u.load_asset(destination) if LIB.does_asset_exist(destination) else LIB.duplicate_asset(source.get_path_name(),destination)
    if not asset:raise RuntimeError('Could not create V05 package: '+destination)
    return asset

def imp(file,name,folder,options):
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True;task.options=options
    AT.import_asset_tasks([task]);asset=u.load_asset(folder+'/'+name)
    if not asset:raise RuntimeError('Import failed: '+name+' '+str(task.imported_object_paths))
    return asset

def render_mesh_options(mesh):
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_mesh=True;options.import_animations=False;options.import_as_skeletal=True
    options.import_materials=False;options.import_textures=False;options.skeleton=mesh.skeleton
    options.create_physics_asset=False;options.physics_asset=mesh.physics_asset
    options.skeletal_mesh_import_data.convert_scene_unit=True
    options.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    options.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
    return options

def finish_render_mesh(mesh):
    # UE's RemoveMeshSection disables a section; it does not remove its source
    # geometry. Reimport the render-only FBX after cloth extraction. The FBX
    # importer backs up and rebinds the original robe's existing cloth data.
    materials={str(s.get_editor_property('imported_material_slot_name')):s.material_interface for s in mesh.materials}
    mesh=imp(ROOT/'Delivery/OriginalRobeV05/SK_Witch_OriginalRobeV05.fbx','SK_Witch_Meshy',DEST,render_mesh_options(mesh))
    slots=list(mesh.materials)
    for slot in slots:
        name=str(slot.get_editor_property('imported_material_slot_name'))
        if name in materials:slot.material_interface=materials[name]
    mesh.set_editor_property('materials',slots)
    LIB.set_metadata_tag(mesh,'RenderGeometry','Original robe only; simulation cage excluded from the render FBX and retained in cloth data')
    save(mesh)
    report['render_geometry']='OriginalRobe only; SimProxy removed from the imported render mesh'
    record('Reimported render-only body, preserving original robe cloth data')
    return mesh

if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('V05 asset authoring requires PIE to be stopped')

phase=globals().get('WITCH_V05_PHASE','import')
if phase=='import':
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    source=u.load_asset(BASE+'/PreviousCloudGripV02/SK_Witch_Meshy')
    skeleton=duplicate(source.skeleton,DEST+'/SK_Witch_OriginalRobeV05_Skeleton')
    physics=duplicate(u.load_asset(BASE+'/LayeredV04/PA_Witch_LayeredV04'),DEST+'/PA_Witch_OriginalRobeV05')
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_mesh=True;options.import_animations=False;options.import_as_skeletal=True
    options.import_materials=False;options.import_textures=False;options.skeleton=skeleton
    options.create_physics_asset=False;options.physics_asset=physics
    options.skeletal_mesh_import_data.convert_scene_unit=True
    options.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    options.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
    mesh=u.load_asset(DEST+'/SK_Witch_Meshy') if 'Imported original robe body and cage' in report['completed'] else None
    if not mesh:mesh=imp(ROOT/'Delivery/OriginalRobeV05/SK_Witch_OriginalRobeV05_ClothBuildSource.fbx','SK_Witch_Meshy',DEST,options)
    record('Imported original robe body and cage')
    body_mat=source.materials[0].material_interface
    cloth=duplicate(body_mat,DEST+'/Materials/M_Witch_V05_OriginalRobe')
    for prop in ['two_sided','used_with_skeletal_mesh','used_with_clothing']:cloth.set_editor_property(prop,True)
    u.MaterialEditingLibrary.recompile_material(cloth);save(cloth)
    inner=u.load_asset(BASE+'/LayeredV04/Materials/M_Witch_V04_InnerBody')
    slots=list(mesh.materials)
    for slot in slots:
        name=str(slot.get_editor_property('imported_material_slot_name'))
        slot.material_interface=cloth if 'OriginalRobe' in name else inner if 'InnerBody' in name else body_mat
    mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',physics)
    LIB.set_metadata_tag(mesh,'SourceLayers','Original Meshy upper body, robe, bare feet and PBR; hidden donor anatomy; hidden 1984-vertex cloth cage')
    LIB.set_metadata_tag(mesh,'GroundReference','Alive animations place the actual skinned original soles on Z=0')
    LIB.set_metadata_tag(mesh,'Status','V05 authored candidate; no preview or runtime test')
    for obj in [mesh,skeleton,physics]:save(obj)
    record('Saved original PBR materials and isolated mesh, skeleton, physics')
    for role in ROLES:
        if 'Saved '+role in report['completed']:continue
        options=u.FbxImportUI();options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        options.skeleton=skeleton;options.import_mesh=False;options.import_animations=True
        options.import_materials=False;options.import_textures=False
        options.anim_sequence_import_data.convert_scene_unit=True
        options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        options.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
        options.anim_sequence_import_data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        clip=imp(ROOT/f'Delivery/OriginalRobeV05/A_Witch_{role}_OriginalRobeV05.fbx','A_Witch_'+role,DEST+'/Animations',options)
        clip.set_preview_skeletal_mesh(mesh)
        clip.set_editor_property('loop',role in ['Walk','Idle'])
        clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
        LIB.set_metadata_tag(clip,'Source','UE female walk plus resampled upper carry layer and original sole placement' if role=='Walk' else 'Meshy cloud V02 with original sole placement; death trajectory preserved')
        save(clip);record('Saved '+role)
    report['assets']=[DEST+'/SK_Witch_Meshy']+[DEST+'/Animations/A_Witch_'+r for r in ROLES]
    record('Import complete; native cloth build and F6 activation pending')
elif phase in ['activate','finish_render']:
    mesh=u.load_asset(DEST+'/SK_Witch_Meshy')
    # Extract once; subsequent activation reuses the saved simulation data.
    # UE's editor utility persists the source-section user data for binding.
    if not mesh.get_editor_property('mesh_clothing_assets'):
        if not u.WitchMonster.prepare_combat_physics(mesh):raise RuntimeError('V05 original render robe cloth extraction did not complete')
    cloth_result=repair_original_robe_cloth(mesh)
    save(mesh.physics_asset);save(mesh)
    if 'Reimported render-only body, preserving original robe cloth data' not in report['completed']:
        mesh=finish_render_mesh(mesh)
        cloth_result=repair_original_robe_cloth(mesh)
    cdo=u.get_default_object(u.load_class(None,'/Script/FPSGAME.WitchMonster'))
    cdo.set_editor_property('visual_mesh',mesh)
    contract=json.loads((OUT/'motion_manifest.json').read_text())
    cdo.set_editor_property('walk_speed',contract['actions']['Walk']['speed_cm_s'])
    for prop,role in [('idle_clip','Idle'),('walk_clip','Walk'),('cast_clip','CastPoison'),('throw_clip','ThrowPoisonBottle'),('death_clip','DeathBackward'),('attack_clip','CastPoison')]:
        cdo.set_editor_property(prop,u.load_asset(DEST+'/Animations/A_Witch_'+role))
    report['walk_speed_cm_s']=cdo.get_editor_property('walk_speed')
    report['cloth']='Original dense render robe mapped to a separate low-poly Chaos cage; cage render section removed; waist pin, body collisions and self collision authored'
    report['cloth_binding']=cloth_result
    if 'duplicate_skirt_cleanup' in report:
        report['duplicate_skirt_cleanup']['cloth_records']=len(cloth_result['clothing_assets'])
        report['duplicate_skirt_cleanup']['cloth_binding_deduplication']='saved'
    report['f6']='Existing Witch native class and navigation profile'
    report['stage']='integrated_pending_user_test'
    record('Saved hidden-cage Chaos cloth and activated V05 for the existing F6 Witch')
print(json.dumps(report,ensure_ascii=False))
