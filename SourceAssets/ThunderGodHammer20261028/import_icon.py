"""Save the inventory Texture2D; module thumbnails use the existing staged PNG loader."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1];ID='ue_thunder_god_hammer'
A=u.AssetToolsHelpers.get_asset_tools()
assets=[]
def texture(source,folder,name):
    asset=u.load_asset(folder+'/'+name)
    if not asset:
        task=u.AssetImportTask();task.filename=str(source);task.destination_path=folder;task.destination_name=name
        task.automated=True;task.save=False
        A.import_asset_tasks([task]);asset=u.load_asset(folder+'/'+name)
    if not asset:raise RuntimeError('Icon import failed: '+str(source))
    asset.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    asset.set_editor_property('srgb',True);asset.set_editor_property('never_stream',True)
    asset.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Icon save failed')
    assets.append(asset.get_path_name())
texture(ROOT/'Content/ColdSteelData/Icons'/(ID+'.png'),'/Game/ColdSteelData/Icons',ID)
base=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
(P/'icon_import_receipt.json').write_text(json.dumps({'complete':True,'assets':assets,
    'module_icons_storage':'staged PNG, consumed by M4GunsmithLayout ImportFileAsTexture2D',
    'module_icon_files':[str(p) for p in sorted(base.glob(ID+'_*.png'))],
    'tested':False},indent=2),encoding='utf-8')
print('THUNDER_GOD_ICONS_SAVED '+str(len(assets)))
