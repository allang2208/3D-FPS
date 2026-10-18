"""Import only the nine reviewed UI Texture2D packages."""
import unreal as u,json,hashlib
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME');O=R/'SourceAssets/Super90IconReview20261016'
D='/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
data=json.loads((O/'deployment.json').read_text(encoding='utf-8'));A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
if (O/'import_receipt.json').exists():raise RuntimeError('A prior import receipt exists; inspect it before resuming')
if u.EditorLevelLibrary.get_game_world():raise RuntimeError('PIE is active; preserve loaded assets')
for item in data['entries']:
    package=(R/item['runtime_png']).with_suffix('.uasset')
    current=hashlib.sha256(package.read_bytes()).hexdigest() if package.exists() else None
    if current!=item['previous_package_sha256']:raise RuntimeError('Package changed since backup: '+str(package))
saved=[]
for item in data['entries']:
    key=item['key'];task=u.AssetImportTask();task.filename=str(R/item['runtime_png']);task.destination_path=D;task.destination_name=key
    task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task]);asset=u.load_asset(D+'/'+key)
    if not isinstance(asset,u.Texture2D):raise RuntimeError('Texture import failed: '+key)
    asset.srgb=True;asset.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
    asset.lod_group=u.TextureGroup.TEXTUREGROUP_UI;asset.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;asset.never_stream=True
    E.set_metadata_tag(asset,'Super90IconReviewSource',item['source']);E.set_metadata_tag(asset,'Super90IconReviewSHA256',item['sha256'])
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Texture save failed: '+key)
    saved.append(dict(key=key,asset=asset.get_path_name(),source_png=task.filename))
    (O/'import_receipt.json').write_text(json.dumps(dict(saved=saved,completed=len(saved)==len(data['entries']),game_or_pie_started=False),indent=2))
print('SUPER90_REVIEW_ICONS_SAVED',len(saved))
