from pathlib import Path
import hashlib, json, os, tempfile
import unreal as u

here = Path(__file__).resolve().parent
project = here.parents[2]
key = 'ue_m249_no_bipod'
raw = (here/'catalog'/f'{key}.png').read_bytes()
if len(raw) < 1000: raise RuntimeError('empty icon')
def publish(dst):
    with tempfile.NamedTemporaryFile(delete=False, dir=dst.parent) as f:
        f.write(raw)
    os.replace(f.name, dst)
png = project/'Content/ColdSteelData/Icons'/f'{key}.png'
asset = '/Game/ColdSteelData/Icons/' + key
if asset in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}: raise RuntimeError('package is dirty')
publish(png)
t = u.AssetImportTask()
t.filename=str(png)
t.destination_path, t.destination_name=asset.rsplit('/',1)
t.automated=True
t.replace_existing=True
t.replace_existing_settings=False
t.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
image=u.load_asset(asset)
if not t.imported_object_paths or not isinstance(image,u.Texture2D): raise RuntimeError('import failed')
for name,value in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,
                       mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,srgb=True,never_stream=True).items():
    image.set_editor_property(name,value)
if not u.EditorAssetLibrary.save_loaded_asset(image, False): raise RuntimeError('save failed')
publish(project/'SourceAssets/InventoryWeaponIcons20261108/Artwork'/png.name)
(here/'published.json').write_text(json.dumps({'package':asset,'png_sha256':hashlib.sha256(raw).hexdigest()}))
