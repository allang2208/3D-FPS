"""Save only the newly deployed TangDao UI textures."""
import json
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
if Path(u.Paths.project_dir()).resolve() != P.parents[1]:
    raise RuntimeError('TangDao icons require the FPSGAME host project.')
rows = json.loads((P / 'icon_deploy_receipt.json').read_text(encoding='utf-8'))
tools = u.AssetToolsHelpers.get_asset_tools()
saved = []
for row in rows:
    path = row['asset']
    task = u.AssetImportTask()
    task.filename = row['destination']
    task.destination_path, task.destination_name = path.rsplit('/', 1)
    task.automated = True
    task.replace_existing = path == '/Game/ColdSteelData/Icons/ue_tang_dao'
    task.save = True
    tools.import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('TangDao UI texture import failed: ' + path)
    texture = u.load_asset(path)
    texture.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('never_stream', True)
    texture.set_editor_property('srgb', True)
    if path == '/Game/ColdSteelData/Icons/ue_tang_dao':
        texture.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    if not u.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()], False):
        raise RuntimeError('TangDao UI texture save failed: ' + path)
    saved.append(path)
    (P / 'icon_import_receipt.json').write_text(json.dumps({'assets': saved, 'complete': False, 'tested': False}, indent=2), encoding='utf-8')
(P / 'icon_import_receipt.json').write_text(json.dumps({'assets': saved, 'complete': True, 'tested': False}, indent=2), encoding='utf-8')
print('TANGDAO_UI_ASSETS_SAVED ' + str(len(saved)))
