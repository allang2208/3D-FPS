"""Replace and save only Far Peak's owned framed icon through the UE batch gate."""
from pathlib import Path
from datetime import datetime
import hashlib, json, shutil
import unreal as u

P = Path(__file__).parent
PROJECT = Path('D:/FPS3D/FPSGAME')
NAME = 'bow_woodsteel_riser_highland_far_peak'
FOLDER = '/Game/ColdSteelData/AttachmentIcons20260913/FramedBows'
PACKAGE = FOLDER + '/' + NAME
SOURCE = P / (NAME + '.png')
ACTIVE = PROJECT / 'Content/ColdSteelData/AttachmentIcons20260913/FramedBows' / (NAME + '.png')
AUTHOR_PNG = P.parent / 'FarPeakV4' / (NAME + '.png')
LEGACY_SCRIPT = P.parent / 'FarPeakV4/author_icon.py'
RECEIPT = P / 'import-receipt.json'
if RECEIPT.exists():
    raise RuntimeError('This production receipt already exists; use a new revision rather than overwrite history.')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_name() == PACKAGE:
        raise RuntimeError('Preserving unsaved icon package: ' + PACKAGE)
texture = u.load_asset(PACKAGE)
if not isinstance(texture, u.Texture2D):
    raise RuntimeError('Expected existing owned Far Peak Texture2D: ' + PACKAGE)
stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
archive = PROJECT / 'trash' / ('FarPeakIconBeforeV6-' + stamp)
archive.mkdir(parents=True)
result = {
    'revision': 'FarPeakIconV6', 'weapon': 'bow_woodsteel', 'slot': 'riser',
    'option_id': 'highland_far_peak', 'package': PACKAGE,
    'source': str(SOURCE), 'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'generated_by': 'built-in imagegen',
    'prompt': str(P / 'imagegen-prompt.txt'),
    'actual_part_input': str(P / 'far_peak_actual_part.png'),
    'frame_master': str(PROJECT / 'SourceAssets/FirearmFramedIcons20260930/muzzle_brake_framed_v2.png'),
    'backup_root': str(archive), 'backups': [],
    'gameplay_tested': False, 'complete': False,
}
for source, label in [(ACTIVE, 'ActiveIcon.png'), (ACTIVE.with_suffix('.uasset'), 'ActiveIcon.uasset'),
                      (AUTHOR_PNG, 'PreviousAuthorIcon.png'), (LEGACY_SCRIPT, 'PreviousAuthorIcon.py')]:
    if source.exists():
        target = archive / label
        shutil.copy2(source, target)
        result['backups'].append({'source': str(source), 'archive': str(target),
                                  'bytes': source.stat().st_size,
                                  'sha256': hashlib.sha256(source.read_bytes()).hexdigest()})
(archive / 'manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
RECEIPT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
shutil.copy2(SOURCE, ACTIVE)
shutil.copy2(SOURCE, AUTHOR_PNG)
task = u.AssetImportTask()
task.filename = str(ACTIVE)
task.destination_path = FOLDER
task.destination_name = NAME
task.automated = True
task.replace_existing = True
task.replace_existing_settings = True
task.save = False
task.factory = u.TextureFactory()
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
imported = list(task.get_objects())
texture = next((obj for obj in imported if isinstance(obj, u.Texture2D) and obj.get_name() == NAME), None)
if not texture:
    raise RuntimeError('Texture import did not return the target icon; receipt retains partial production state.')
texture.lod_group = u.TextureGroup.TEXTUREGROUP_UI
texture.compression_settings = u.TextureCompressionSettings.TC_EDITOR_ICON
texture.mip_gen_settings = u.TextureMipGenSettings.TMGS_NO_MIPMAPS
texture.srgb = True
texture.max_texture_size = 1024
texture.set_editor_property('never_stream', True)
if not u.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()], False):
    raise RuntimeError('Far Peak icon package save failed.')
result.update({
    'complete': True, 'saved_asset': texture.get_path_name(),
    'active_png': str(ACTIVE), 'author_png': str(AUTHOR_PNG),
    'saved_at': datetime.now().isoformat(),
    'texture_settings': {'lod_group': 'UI', 'compression': 'EditorIcon', 'srgb': True,
                         'never_stream': True, 'mips': 'NoMipmaps', 'max_texture_size': 1024},
    'native_build_required': False,
})
RECEIPT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('FAR_PEAK_ICON_V6_SAVED ' + texture.get_path_name(), flush=True)
