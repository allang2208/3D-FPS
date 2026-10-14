"""Import author-provided free full-body donors into a new, isolated UE folder."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/ThirdPersonSwordFree20261005'
DEST = '/Game/Characters/JasonPlayer20261003/SwordFullBody20261005'
lib = u.EditorAssetLibrary
assets = u.AssetToolsHelpers.get_asset_tools()


def import_fbx(path, folder, name, skeleton=None, animations=False):
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION if skeleton else u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal = not bool(skeleton)
    options.import_mesh = not bool(skeleton)
    options.import_animations = animations
    options.import_materials = False
    options.import_textures = False
    options.create_physics_asset = False
    if skeleton:
        options.skeleton = skeleton
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate', 30)
    task = u.AssetImportTask()
    task.filename = str(path)
    task.destination_path = DEST + '/Donors/' + folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = False
    task.save = True
    task.options = options
    task.factory = u.FbxFactory()
    if lib.does_asset_exist(task.destination_path + '/' + name):
        raise RuntimeError('Existing candidate: ' + name)
    assets.import_asset_tasks([task])
    # Legacy FBX reports the mesh only, even when it creates a skeleton and
    # multiple animation takes. Save all newly created packages in this folder.
    imported = [u.load_asset(p) for p in lib.list_assets(task.destination_path, True, False)]
    for asset in imported:
        if not lib.save_loaded_asset(asset, False):
            raise RuntimeError('Could not save imported dependency: ' + asset.get_path_name())
    return imported


result = {}
kevin = import_fbx(OUT/'Kevin/Models/HumanM_Model.fbx', 'Kevin', 'SK_Kevin_HumanM')
mesh = next(a for a in kevin if isinstance(a, u.SkeletalMesh))
clips = []
for name in ('Attack2H01', 'CombatIdle2H01'):
    clips += import_fbx(OUT/f'Kevin/Animations/Male/Combat/2H/HumanM@{name}.fbx',
                        'Kevin', 'A_Kevin_' + name, mesh.skeleton, True)
result['Kevin'] = {'mesh': mesh.get_path_name(), 'clips': {
    a.get_name(): a.get_path_name() for a in clips if isinstance(a, u.AnimSequence)}}

kaykit = import_fbx(OUT/'KayKit/KayKit_Character_Animations_1.1/Animations/fbx/Rig_Medium/Rig_Medium_CombatMelee.fbx',
                   'KayKit', 'SK_KayKit_Medium', animations=True)
mesh = next(a for a in kaykit if isinstance(a, u.SkeletalMesh))
result['KayKit'] = {'mesh': mesh.get_path_name(), 'clips': {
    a.get_name(): a.get_path_name() for a in kaykit if isinstance(a, u.AnimSequence)}}

(OUT/'imported-sources.json').write_text(json.dumps(result, indent=2), encoding='utf-8')

# Read the existing head post-process graph as part of the reported distortion
# diagnosis. Exporting text does not save or change the existing blueprint.
bp = u.load_asset('/Game/AsianMale_Jason/Demo/MetaHumans/Common/Face/ABP_Face_PostProcess')
if bp:
    task = u.AssetExportTask()
    task.object = bp
    task.filename = str(OUT/'head-postprocess.t3d')
    task.exporter = u.ObjectExporterT3D()
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    u.Exporter.run_asset_export_task(task)
print('FREE_SWORD_IMPORTED ' + json.dumps(result))
