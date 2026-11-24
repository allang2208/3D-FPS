"""Import four viewmodel bodies into an isolated content host, binding the existing R2 skeleton."""
from pathlib import Path
import json
import os
import unreal as ue

source = Path(__file__).resolve().parent
batch = Path(os.environ['FRONTIER_BATCH'])
root = '/Game/Weapons/FrontierCompoundBow'
destination = root + '/FrameVariantsR1'
skeleton = ue.load_asset(root + '/RigContactR2/SK_Frontier_Assembly_Skeleton')
if not skeleton:
    raise RuntimeError('Missing R2 skeleton')
materials = {key:ue.load_asset(root + '/' + path) for key,path in {
    'M_Frontier_Surface':'M_Frontier_Surface',
    'M_Frontier_Cord':'M_Frontier_Cord',
    'M_FrontierMods_Surface':'CommonModsR1/M_FrontierMods_Surface'}.items()}
ue.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
tools = ue.AssetToolsHelpers.get_asset_tools()
skins = ue.get_editor_subsystem(ue.SkeletalMeshEditorSubsystem) or ue.new_object(ue.SkeletalMeshEditorSubsystem)
frames = json.loads((source/'frames.json').read_text(encoding='utf8'))
saved = {}
for key,frame in frames.items():
    name = 'SK_Frontier_' + frame['model'] + 'Frame'
    options = ue.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = ue.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal = True
    options.import_mesh = True
    options.import_animations = False
    options.import_materials = False
    options.import_textures = False
    options.create_physics_asset = False
    options.skeleton = skeleton
    settings = options.skeletal_mesh_import_data
    settings.normal_import_method = ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    settings.set_editor_property('use_t0_as_ref_pose',False)
    settings.set_editor_property('update_skeleton_reference_pose',False)
    task = ue.AssetImportTask()
    task.filename = str(source/'Export'/(name+'.fbx'))
    task.destination_name = name
    task.destination_path = destination
    task.options = options
    task.automated = True
    task.replace_existing = True
    tools.import_asset_tasks([task])
    mesh = ue.load_asset(destination+'/'+name)
    if not mesh or mesh.skeleton != skeleton:
        raise RuntimeError('Unable to import against R2: '+name)
    slots = list(mesh.materials)
    for slot in slots:
        material = materials.get(str(slot.material_slot_name))
        if not material:
            raise RuntimeError(f'{name}: unbound material {slot.material_slot_name}')
        slot.material_interface = material
    mesh.materials = slots
    if not skins.regenerate_lod(mesh,3,False,False):
        raise RuntimeError('Unable to build world LODs for '+name)
    if not ue.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):
        raise RuntimeError('Unable to save '+name)
    saved[key] = mesh.get_path_name()

(batch/'imported.json').write_text(json.dumps({'skeleton':skeleton.get_path_name(),'meshes':saved},indent=2),encoding='utf8')
