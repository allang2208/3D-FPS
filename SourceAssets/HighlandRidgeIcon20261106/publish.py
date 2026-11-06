"""Replace the live ridge-piercer modification icon with its framed source."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import shutil
import unreal as u

P=Path(__file__).resolve().parent
root=P.parents[1]
if Path(u.Paths.project_dir()).resolve()!=root.resolve():
    raise RuntimeError('Wrong editor project')
name='ue_highland_claymore_blade_1_highland_ridge_piercer'
source=P/(name+'.png')
destination=root/'Content/ColdSteelData/AttachmentIcons20260913'/(name+'.png')
package='/Game/ColdSteelData/AttachmentIcons20260913/'+name
if any(p.get_path_name()==package for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserving unsaved ridge icon edits')
before=P/'Before'/datetime.now().strftime('%Y%m%d-%H%M%S')
before.mkdir(parents=True,exist_ok=True)
for file in (destination,destination.with_suffix('.uasset')):
    if file.exists():shutil.copy2(file,before/file.name)
shutil.copy2(source,destination)
task=u.AssetImportTask()
task.filename=str(destination)
task.destination_path=package.rsplit('/',1)[0]
task.destination_name=name
task.factory=u.TextureFactory()
task.automated=True
task.replace_existing=True
task.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture=u.load_asset(package)
if not task.imported_object_paths or not isinstance(texture,u.Texture2D):
    raise RuntimeError('Ridge framed icon import failed')
texture.set_editor_properties(dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,
    compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,
    srgb=True,never_stream=True,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS))
u.EditorAssetLibrary.set_metadata_tag(texture,'HighlandIconRevision','FramedR4_20261106')
if not u.EditorAssetLibrary.save_loaded_asset(texture,False):
    raise RuntimeError('Ridge framed icon was not saved')
(P/'import_receipt.json').write_text(json.dumps(dict(source=str(source),destination=str(destination),
    asset=texture.get_path_name(),saved=True,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    model_revision='WedgeSpineJunctionR4_20261106',runtime_tested=False),indent=2),encoding='utf-8')
print('RIDGE_FRAMED_ICON_SAVED '+texture.get_path_name())
