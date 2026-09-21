"""Import V06 repairs into the existing F6 Witch asset. No PIE or acceptance run."""
import unreal as u,json
from pathlib import Path

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchMeshy20260919')
DEST='/Game/Monsters/WitchMeshy/OriginalRobeV05'
PATH=DEST+'/SK_Witch_Meshy'
REPORT=Path(globals().get('WITCH_V06_REPORT_FILE',ROOT/'ue_clean_robe_v06.json'))
LIB=u.EditorAssetLibrary
AT=u.AssetToolsHelpers.get_asset_tools()
report=json.loads(REPORT.read_text(encoding='utf-8')) if REPORT.exists() else {'revision':'CleanRobeV06','completed':[],'runtime_tested':False}

def record(stage):
    if stage not in report['completed']:report['completed'].append(stage)
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('V06_IMPORT_STAGE '+stage,flush=True)

def save(obj):
    if not LIB.save_loaded_asset(obj,False):raise RuntimeError('Save failed: '+obj.get_path_name())

def prepare_cloth(mesh):
    if not u.WitchMonster.prepare_combat_physics(mesh):raise RuntimeError('V06 cloth authoring did not complete')
    if not any(c.get_name().startswith('Witch_CleanRobe_ChaosV06Cm') for c in mesh.get_editor_property('mesh_clothing_assets')):
        raise RuntimeError('Centimetre cloth authoring code is not loaded; keep the imported source unsaved for resume')

def import_body(filename,mesh):
    # Reimport can reuse the mesh's saved FBX data instead of FbxImportUI.
    # Pin centimetre conversion on both inputs; animation assets already use it.
    source_data=mesh.get_editor_property('asset_import_data')
    source_data.set_editor_property('convert_scene',True)
    source_data.set_editor_property('convert_scene_unit',True)
    source_data.set_editor_property('import_uniform_scale',1.0)
    source_data.set_editor_property('import_translation',u.Vector(0,0,0))
    source_data.set_editor_property('import_rotation',u.Rotator(0,0,0))
    source_data.set_editor_property('force_front_x_axis',False)
    opts=u.FbxImportUI();opts.automated_import_should_detect_type=False
    opts.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    opts.import_mesh=True;opts.import_animations=False;opts.import_as_skeletal=True
    opts.import_materials=False;opts.import_textures=False
    opts.skeleton=mesh.skeleton;opts.physics_asset=mesh.physics_asset;opts.create_physics_asset=False
    opts.skeletal_mesh_import_data.convert_scene_unit=True
    opts.skeletal_mesh_import_data.convert_scene=True
    opts.skeletal_mesh_import_data.import_uniform_scale=1.0
    opts.skeletal_mesh_import_data.import_translation=u.Vector(0,0,0)
    opts.skeletal_mesh_import_data.import_rotation=u.Rotator(0,0,0)
    opts.skeletal_mesh_import_data.force_front_x_axis=False
    opts.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    opts.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
    task=u.AssetImportTask();task.filename=str(ROOT/'Delivery/CleanRobeV06'/filename)
    task.destination_path=DEST;task.destination_name='SK_Witch_Meshy'
    task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True;task.options=opts
    task.factory=u.FbxFactory()
    AT.import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('FBX import did not produce an asset: '+filename)
    result=u.load_asset(PATH)
    body=u.load_asset('/Game/Monsters/WitchMeshy/Materials/M_Witch_Body')
    cloth=u.load_asset(DEST+'/Materials/M_Witch_V05_OriginalRobe')
    slots=list(result.materials)
    for slot in slots:
        name=str(slot.get_editor_property('imported_material_slot_name'))
        slot.material_interface=cloth if 'OriginalRobe' in name else body
    result.set_editor_property('materials',slots)
    return result

if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE is running. Keep the scene; V06 import has not started.')
mesh=u.load_asset(PATH)
resume_source=bool(globals().get('WITCH_V06_RESUME_SOURCE',False))
dirty=u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
if any(p.get_path_name()==PATH for p in dirty) and not resume_source:
    raise RuntimeError('Target Witch mesh has unsaved edits; retained without importing over it.')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')

if 'cloth_extraction_saved' not in report['completed']:
    if not resume_source:mesh=import_body('SK_Witch_CleanRobeV06_ClothBuildSource.fbx',mesh)
    prepare_cloth(mesh)
    save(mesh.physics_asset);save(mesh)
    record('cloth_extraction_saved')

if 'render_mesh_saved' not in report['completed']:
    mesh=import_body('SK_Witch_CleanRobeV06.fbx',mesh)
    prepare_cloth(mesh)
    LIB.set_metadata_tag(mesh,'SourceRevision','CleanRobeV06')
    LIB.set_metadata_tag(mesh,'RenderGeometry','Seven original Meshy parts; no donor body/hands/calves; no simulation cage')
    LIB.set_metadata_tag(mesh,'ClothAnchors','Matched waist and ankle skin; 6 cm maximum middle-drape displacement; dedicated collisions')
    LIB.set_metadata_tag(mesh,'Status','Imported and saved; user gameplay test pending')
    save(mesh.physics_asset);save(mesh)
    record('render_mesh_saved')

cdo=u.get_default_object(u.load_class(None,'/Script/FPSGAME.WitchMonster'))
cdo.set_editor_property('visual_mesh',mesh)
report.update({'mesh':mesh.get_path_name(),'source_fbx':str(ROOT/'Delivery/CleanRobeV06/SK_Witch_CleanRobeV06.fbx'),
    'f6':'Existing Witch entry /Script/FPSGAME.WitchMonster',
    'animations_reimported':False,'stage':'integrated_pending_user_test'})
record('existing_f6_witch_updated')
print(json.dumps(report,ensure_ascii=False))
