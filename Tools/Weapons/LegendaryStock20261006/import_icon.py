"""Save the shared grayscale framed icon and its production receipt."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parents[3];O=P/'SourceAssets/LegendaryStock20261006/RefinementV3'
source=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/stock_legendary_adjustable_tactical_stock.png'
dest='/Game/Weapons/LegendaryStock20261006/Icons';name='T_TacticalStockIcon'
if dest+'/'+name in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:raise RuntimeError('Preserve unsaved stock icon')
task=u.AssetImportTask();task.filename=str(source);task.destination_path=dest;task.destination_name=name
task.automated=True;task.replace_existing=True;task.save=False;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture=u.load_asset(dest+'/'+name)
if texture is None or not task.imported_object_paths:raise RuntimeError('Stock icon import failed')
texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);texture.set_editor_property('srgb',True)
texture.set_editor_property('never_stream',True)
if not u.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()],False):raise RuntimeError('Stock icon save failed')
receipt={'source':str(source),'texture':texture.get_path_name(),'saved':True,'game_tested':False,
 'visual_revision':'V3_concave_shoulder_contact',
 'generator':'Built-in imagegen; actual Blender model icon source and approved metal frame references',
 'prompt':str(O/'icon-prompt.txt')}
(O/'icon-import-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('TACTICAL_STOCK_ICON_SAVED '+texture.get_path_name())
