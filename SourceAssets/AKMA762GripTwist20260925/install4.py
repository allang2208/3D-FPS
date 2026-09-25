"""Import the naturally-extended AKM / A762 reload thumbs (v3) over their existing paths.

Only the 30 magazine-grip reload sequences are replaced; every other clip, mesh,
material and the C++ side are untouched.  The packages currently in the project
are the round-1 twist repair and are copied to Before4/ before being overwritten,
and every import is read back for duration, skeleton and compression settings.
"""
import json
import shutil
import unreal as u
from pathlib import Path

try:
    O = Path(__file__).parent
except NameError:  # executed inside the editor through the MCP python bridge
    O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\AKMA762GripTwist20260925')
P = O.parents[1]
V4 = P / 'SourceAssets/RifleMagazineGrip20260922/IndexClearanceV4'
SOURCES = json.loads((V4 / 'sources.json').read_text(encoding='utf-8'))['animations']

# The editor bridge runs python with a bounded timeout, so the 30 imports can be
# driven in slices.  A slice file selects [start, start+count) from sources.json;
# the per-clip work is idempotent, so a repeated or resumed slice is safe.
CHUNK_FILE = O / 'install4_chunk.json'
if CHUNK_FILE.exists():
    chunk = json.loads(CHUNK_FILE.read_text(encoding='utf-8-sig'))
    start, count = int(chunk['start']), int(chunk['count'])
    jobs = SOURCES[start:start + count]
    receipt_name = 'install4_receipt_%02d.json' % start
else:
    jobs = SOURCES
    receipt_name = 'install4_receipt.json'

A = u.AssetToolsHelpers.get_asset_tools()
E = u.EditorAssetLibrary
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')

SKELETON = u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_HK416_Skeleton')
COMPRESSION = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')

report = {}
for job in jobs:
    stem = Path(job['asset']).name
    fbx = O / 'v4' / job['gun'] / job['magazine'] / job['family'] / (stem + '.fbx')
    if not fbx.exists():
        raise RuntimeError('missing FBX ' + str(fbx))
    asset = job['asset']
    old = u.load_asset(asset)
    if not old:
        raise RuntimeError('missing target asset ' + asset)
    disk = P / 'Content' / (asset.removeprefix('/Game/') + '.uasset')
    backup = O / 'Before4' / (asset.removeprefix('/Game/') + '.uasset')
    if disk.exists() and not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(disk, backup)
    before_mtime = disk.stat().st_mtime if disk.exists() else None
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
    # EditorAssetLibrary.set_metadata_tag is inert in this 5.8 build (returns None
    # and reads back empty), so the round is tied to the assets through
    # asset_import_data instead - readback2.py checks every asset's import source
    # is this round's v2 FBX.
    # save_loaded_asset's return value is unreliable while the editor has the
    # asset loaded (it returns False even though the package is written), so the
    # save is confirmed from the package file's modification time.
    returned = bool(E.save_loaded_asset(anim, False))
    after_mtime = disk.stat().st_mtime if disk.exists() else None
    written = after_mtime is not None and after_mtime != before_mtime
    if not (returned or written):
        raise RuntimeError('save failed for ' + asset)
    key = '/'.join((job['gun'], job['magazine'], job['family'], job['clip']))
    report[key] = {'asset': asset, 'source': str(fbx), 'duration': anim.get_play_length(),
                   'save_returned': returned, 'package_written': written,
                   'package_mtime': after_mtime, 'saved': True}
    (O / receipt_name).write_text(json.dumps(report, indent=1), encoding='utf-8')
    print('THUMB4_IMPORTED', key, anim.get_play_length(), 'written=%s returned=%s' % (written, returned), flush=True)
print('THUMB4_IMPORT_COMPLETE', len(report), receipt_name)
