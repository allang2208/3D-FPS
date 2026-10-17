"""Save only the new M870 UI texture packages; no gameplay or map changes."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/M870FactoryIcons20261016'
DEST='/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
data=json.loads((OUT/'deployment.json').read_text())
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
saved=[]
for item in data['entries']:
    key=item['key'];path=DEST+'/'+key
    if E.does_asset_exist(path):raise RuntimeError('Unexpected existing M870 icon asset; preserve it: '+path)
    task=u.AssetImportTask();task.filename=str(ROOT/item['runtime_png']);task.destination_path=DEST;task.destination_name=key
    task.automated=True;task.replace_existing=False;task.save=False
    A.import_asset_tasks([task]);asset=u.load_asset(path)
    if not isinstance(asset,u.Texture2D):raise RuntimeError('Missing imported texture: '+path)
    asset.set_editor_property('srgb',True)
    asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    asset.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    asset.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    asset.set_editor_property('never_stream',True)
    E.set_metadata_tag(asset,'M870FactoryIconSource',item['source'])
    E.set_metadata_tag(asset,'M870FactoryIconSHA256',item['sha256'])
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Texture save failed: '+path)
    saved.append({'key':key,'asset':asset.get_path_name(),'source_png':task.filename})
    (OUT/'import_receipt.json').write_text(json.dumps({'saved':saved,'completed':len(saved)==len(data['entries']),
        'game_or_pie_started':False},indent=2))
print('M870_FACTORY_ICONS_SAVED',len(saved))
