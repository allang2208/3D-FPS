"""Import the grip-refined M4 and M16 reload clips.

Runs inside UE (headless commandlet when no editor is open, MCP bridge when one
is).  Replaces only the twelve reload sequences involved; every other clip,
mesh, material and the C++ side are untouched.  Existing packages are backed up
under Before/ before being overwritten, and each import is read back for
duration, skeleton and compression settings.
"""
import json
import shutil
import unreal as u
from pathlib import Path

O = Path(__file__).parent
P = O.parents[1]
SPEC = json.loads((O / 'grip_fix.json').read_text(encoding='utf-8'))
M16 = json.loads((O / 'm16_grip_authoring.json').read_text(encoding='utf-8'))
A = u.AssetToolsHelpers.get_asset_tools()
E = u.EditorAssetLibrary
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')

COMPRESSION = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
M4_SKELETON = u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416').skeleton
M16_SKELETON = u.load_asset('/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny').skeleton

FOLDERS = {
    'base': '/Game/Weapons/M16A2/Gameplay20260919/Animations',
    'vertical': '/Game/Weapons/M16A2/UniversalAttachments20260920/Animations/vertical',
    'canted': '/Game/Weapons/M16A2/UniversalAttachments20260920/Animations/canted',
    'prism': '/Game/Weapons/M16A2/UniversalAttachments20260920/Animations/prism',
    'angled': '/Game/Weapons/M16A2/UniversalAttachments20260920/Animations/angled',
}

JOBS = []
for kind, spec in SPEC['clips'].items():
    JOBS.append({
        'asset': '/Game/Weapons/ExtMagContact20260919/' + spec['action'],
        'fbx': str(O / 'M4Animations' / (spec['action'] + '_GripPrecise.fbx')),
        'rate': 480, 'skeleton': M4_SKELETON, 'tag': 'M4 grip refinement 2026-09-25',
    })
for key, clip in M16['clips'].items():
    family, kind = key.split('/')
    name = 'A_M16_' + ('' if family == 'base' else family + '_') + kind
    JOBS.append({
        'asset': FOLDERS[family] + '/' + name,
        'fbx': clip['fbx'],
        'rate': 120, 'skeleton': M16_SKELETON, 'tag': 'M16 magazine-frame grip registration 2026-09-25',
    })

report = {}
for job in JOBS:
    fbx = Path(job['fbx'])
    if not fbx.exists():
        raise RuntimeError('missing FBX ' + str(fbx))
    old = u.load_asset(job['asset'])
    if not old:
        raise RuntimeError('missing target asset ' + job['asset'])
    disk = P / 'Content' / (job['asset'].removeprefix('/Game/') + '.uasset')
    backup = O / 'Before' / (job['asset'].removeprefix('/Game/') + '.uasset')
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
    options.skeleton = job['skeleton']
    data = options.anim_sequence_import_data
    data.set_editor_property('use_default_sample_rate', False)
    data.set_editor_property('custom_sample_rate', job['rate'])
    task = u.AssetImportTask()
    task.filename = str(fbx)
    task.destination_path = job['asset'].rsplit('/', 1)[0]
    task.destination_name = job['asset'].rsplit('/', 1)[1]
    task.automated = True
    task.replace_existing = True
    task.save = True
    task.options = options
    A.import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('import returned no objects for ' + job['asset'])
    anim = u.load_asset(job['asset'])
    if anim.get_editor_property('skeleton') != job['skeleton']:
        raise RuntimeError('skeleton mismatch after import: ' + job['asset'])
    anim.set_editor_property('bone_compression_settings', COMPRESSION)
    E.set_metadata_tag(anim, 'GripRefinement', job['tag'])
    if not E.save_loaded_asset(anim, False):
        raise RuntimeError('save failed for ' + job['asset'])
    report[job['asset']] = {
        'source': str(fbx), 'duration': anim.get_play_length(),
        'skeleton': anim.get_editor_property('skeleton').get_path_name(),
        'saved': True, 'imported': [str(p) for p in task.imported_object_paths],
    }
    (O / 'install_receipt.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
    print('GRIP_IMPORTED', job['asset'], anim.get_play_length(), flush=True)
print('GRIP_IMPORT_COMPLETE', len(report))
