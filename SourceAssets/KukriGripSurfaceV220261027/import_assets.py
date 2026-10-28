"""Import nine PBR maps and three framed icons; no mesh or gameplay changes."""
import json
from datetime import datetime
from pathlib import Path
import unreal as u
P = Path(r'D:/FPS3D/FPSGAME/SourceAssets/KukriGripSurfaceV220261027')
jobs = json.loads((P / 'import-jobs.json').read_text(encoding='utf-8'))
tools = u.AssetToolsHelpers.get_asset_tools()
receipt = {'complete': False, 'started': datetime.now().astimezone().isoformat(), 'saved_assets': [],
           'geometry_changed': False, 'uv_changed': False, 'numeric_changes': False, 'runtime_tested': False,
           'authoring_project': u.Paths.project_dir(), 'published_to_game': False}
for job in jobs:
    if not Path(job['source_image']).exists():
        raise RuntimeError('Production image is missing: ' + job['source_image'])
for job in jobs:
    folder, name = job['package'].rsplit('/', 1)
    task = u.AssetImportTask()
    task.filename = job['source_image']
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = True
    task.save = False
    task.factory = u.TextureFactory()
    tools.import_asset_tasks([task])
    asset = u.load_asset(job['package'])
    if not task.imported_object_paths or not asset:
        raise RuntimeError('Texture import failed: ' + name)
    channel = job['channel']
    asset.set_editor_property('srgb', channel in ('BaseColor', 'Icon'))
    asset.set_editor_property('compression_settings', {
        'BaseColor': u.TextureCompressionSettings.TC_BC7,
        'ORM': u.TextureCompressionSettings.TC_MASKS,
        'Normal': u.TextureCompressionSettings.TC_NORMALMAP,
        'Icon': u.TextureCompressionSettings.TC_EDITOR_ICON}[channel])
    asset.set_editor_property('lod_group', {
        'BaseColor': u.TextureGroup.TEXTUREGROUP_WEAPON,
        'ORM': u.TextureGroup.TEXTUREGROUP_WEAPON_SPECULAR,
        'Normal': u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP,
        'Icon': u.TextureGroup.TEXTUREGROUP_UI}[channel])
    asset.set_editor_property('never_stream', channel == 'Icon')
    asset.set_editor_property('max_texture_size', 1024 if channel == 'Icon' else 2048)
    asset.set_editor_property('flip_green_channel', channel == 'Normal')
    asset.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS if channel == 'Icon' else u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
    u.EditorAssetLibrary.set_metadata_tag(asset, 'Kukri.SurfaceRevision', 'GripSurfaceV2-20261027')
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Saving texture failed: ' + name)
    receipt['saved_assets'].append({'asset': asset.get_path_name(), 'channel': channel, 'source': job['source_image']})
    (P / 'Receipts/import-assets.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
receipt['complete'] = True
(P / 'Receipts/import-assets.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('KUKRI_GRIP_SURFACE_V2_SAVED ' + str(len(receipt['saved_assets'])))
