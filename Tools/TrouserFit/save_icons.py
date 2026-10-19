"""Import the updated item thumbnails; keep source family textures unchanged."""
import json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/TrouserFit20261018';E=u.EditorAssetLibrary
receipt=json.loads((R/'saved_assets.json').read_text());receipt['icons']={}
for item in ('ue_leather_pants','ue_chainmail_pants'):
    folder='/Game/ColdSteelData/Icons/TrouserFit20261018';t=u.AssetImportTask();t.filename=str(R/(item+'.png'));t.destination_path=folder;t.destination_name=item;t.automated=True;t.replace_existing=True;t.save=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);asset=u.load_asset(folder+'/'+item)
    asset.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON);asset.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);asset.set_editor_property('srgb',True);asset.modify()
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+item)
    receipt['icons'][item]=asset.get_path_name()
(R/'saved_assets.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print('TROUSER_FIT_ICONS_SAVED',flush=True)
