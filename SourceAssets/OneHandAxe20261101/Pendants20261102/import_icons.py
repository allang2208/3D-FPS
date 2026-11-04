"""Save only the two missing shared pendant Texture2D assets."""
import json
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
jobs = json.loads((P / 'icon_deployments.json').read_text('utf-8'))
dest = '/Game/ColdSteelData/AttachmentIcons20260913'
owned = {dest + '/' + job['key'] for job in jobs}
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if owned & dirty:
    raise RuntimeError('Shared pendant icons have unsaved editor changes; preserved')
project_dir = Path(u.Paths.project_dir()).resolve()
receipt = {'complete': False, 'saved_assets': [], 'reused_assets': [], 'runtime_tested': False,
           'project_dir': str(project_dir), 'saved_to_target_project': project_dir == P.parents[2]}
tools = u.AssetToolsHelpers.get_asset_tools()
for job in jobs:
    path = dest + '/' + job['key']
    if u.EditorAssetLibrary.does_asset_exist(path):
        receipt['reused_assets'].append(path)
        continue
    task = u.AssetImportTask()
    task.filename = job['source']
    task.destination_path = dest
    task.destination_name = job['key']
    task.automated = True
    task.replace_existing = False
    task.save = False
    tools.import_asset_tasks([task])
    tex = u.load_asset(path)
    if not tex or not task.imported_object_paths:
        raise RuntimeError('Pendant icon import failed: ' + job['key'])
    tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_UI)
    tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_EDITOR_ICON)
    tex.set_editor_property('srgb', True)
    tex.set_editor_property('never_stream', True)
    tex.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    tex.set_editor_property('max_texture_size', 1024)
    if not u.EditorLoadingAndSavingUtils.save_packages([tex.get_outermost()], False):
        raise RuntimeError('Pendant icon save failed: ' + job['key'])
    receipt['saved_assets'].append(tex.get_path_name())
    (P / 'icon_import_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
receipt['complete'] = True
(P / 'icon_import_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
u.log('HATCHET_PENDANT_SHARED_ICONS_SAVED')
