"""Save the matching 3x3 ST6 inventory icon, without changing other items."""
import json,shutil,hashlib
from pathlib import Path
import unreal as u
O=Path(__file__).parent;R=O.parents[1]
file=O/'ue_st6_sleeves.png'
relative=Path('ColdSteelData/Icons/Super90Source20261006/ue_st6_sleeves.uasset')
backup=O/'Before/Assets'/relative
if (R/'Content'/relative).exists() and not backup.exists():
    backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/'Content'/relative,backup)
t=u.AssetImportTask();t.filename=str(file);t.destination_path='/Game/ColdSteelData/Icons/Super90Source20261006';t.destination_name='ue_st6_sleeves';t.automated=True;t.replace_existing=True;t.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
asset=u.load_asset(t.destination_path+'/'+t.destination_name)
if not asset:raise RuntimeError('ST6 icon import failed')
asset.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
asset.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
asset.set_editor_property('srgb',True)
if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('ST6 icon save failed')
(O/'icon_saved.json').write_text(json.dumps(dict(asset=asset.get_path_name(),saved=True,source_sha256=hashlib.sha256(file.read_bytes()).hexdigest()),indent=2))
print('ST6_REFINED_ICON_SAVED',flush=True)
