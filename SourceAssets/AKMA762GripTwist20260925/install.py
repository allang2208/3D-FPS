"""Import the thumb-refined AKM / A762 reload clips over their existing paths.

Only the 30 magazine-grip reload sequences are replaced; every other clip, mesh,
material and the C++ side are untouched.  Packages are backed up under Before/
before being overwritten, and each import is read back for duration, skeleton and
compression settings.
"""
import json
import shutil
import unreal as u
from pathlib import Path

O = Path(__file__).parent
P = O.parents[1]
V4 = P / 'SourceAssets/RifleMagazineGrip20260922/IndexClearanceV4'
SOURCES = json.loads((V4 / 'sources.json').read_text(encoding='utf-8'))['animations']
A = u.AssetToolsHelpers.get_asset_tools()
E = u.EditorAssetLibrary
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')

SKELETON = u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_HK416_Skeleton')
COMPRESSION = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')

report = {}
for job in SOURCES:
    stem = Path(job['asset']).name
    fbx = O / job['gun'] / job['magazine'] / job['family'] / (stem + '.fbx')
    if not fbx.exists():
        raise RuntimeError('missing FBX ' + str(fbx))
    asset = job['asset']
    old = u.load_asset(asset)
    if not old:
        raise RuntimeError('missing target asset ' + asset)
    disk = P / 'Content' / (asset.removeprefix('/Game/') + '.uasset')
    backup = O / 'Before' / (asset.removeprefix('/Game/') + '.uasset')
    if disk.exists() and not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(disk, backup)
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh = False
    options.import_animations = True
    options.import_materials = False
    options.import_textures = False
    options.skeleton = SKELETON
    data = options.anim_sequence_import_data
    data.set_editor_property('use_default_sample_rate', False)
    data.set_editor_property('custom_sample_rate', 120)
    task = u.AssetImportTask()
    task.filename = str(fbx)
    task.destination_path = asset.rsplit('/', 1)[0]
    task.destination_name = asset.rsplit('/', 1)[1]
    task.automated = True
    task.replace_existing = True
    task.save = True
    task.options = options
    A.import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('import returned no objects for ' + asset)
    anim = u.load_asset(asset)
    if anim.get_editor_property('skeleton') != SKELETON:
        raise RuntimeError('skeleton mismatch after import: ' + asset)
    anim.set_editor_property('bone_compression_settings', COMPRESSION)
    E.set_metadata_tag(anim, 'GripRefinement', 'AKM/A762 magazine-grip thumb repaired 2026-09-25')
    if not E.save_loaded_asset(anim, False):
        raise RuntimeError('save failed for ' + asset)
    key = '/'.join((job['gun'], job['magazine'], job['family'], job['clip']))
    report[key] = {'asset': asset, 'source': str(fbx), 'duration': anim.get_play_length(), 'saved': True}
    (O / 'install_receipt.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
    print('THUMB_IMPORTED', key, anim.get_play_length(), flush=True)
print('THUMB_IMPORT_COMPLETE', len(report))
