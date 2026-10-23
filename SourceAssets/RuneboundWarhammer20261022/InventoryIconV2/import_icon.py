"""Refresh only the weapon's existing UI texture from the native catalog capture."""
import json
from pathlib import Path
import unreal as u

P=Path(__file__).resolve().parent;ROOT=P.parents[2]
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Preserve current PIE state')
receipt=json.loads((P/'production_receipt.json').read_text(encoding='utf-8'))
if not receipt.get('complete'):raise RuntimeError('Finish native icon authoring first')
source=Path(receipt['author_export'])
dest='/Game/ColdSteelData/Icons';name='ue_runebound_warhammer';path=dest+'/'+name
E=u.EditorAssetLibrary
if any(str(pkg.get_name())==path for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved inventory icon package '+path)
asset=u.load_asset(path) if E.does_asset_exist(path) else None
if asset and not isinstance(asset,u.Texture2D):raise RuntimeError('Preserve non-texture asset '+path)
task=u.AssetImportTask();task.filename=str(source);task.destination_path=dest;task.destination_name=name
task.automated=True;task.replace_existing=True;task.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
icon=u.load_asset(path)
if not isinstance(icon,u.Texture2D):raise RuntimeError('Inventory texture import failed')
for key,value in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,
    compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,
    mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,
    srgb=True,never_stream=True).items():icon.set_editor_property(key,value)
if not E.save_loaded_asset(icon,False):raise RuntimeError('Inventory texture save failed')
result={'complete':True,'asset':icon.get_path_name(),'source':str(source),'canvas':receipt['canvas'],
    'settings':'UI / EditorIcon / sRGB / NeverStream / NoMipmaps','tests_run':False,'game_started':False,'acceptance_rendered':False}
(P/'import_receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('RUNEBOUND_INVENTORY_TEXTURE_SAVED '+json.dumps(result))
