"""Save matching UE Texture2D copies of the actual installed PNGs."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).parent;A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
rows=json.loads((P/'icon-install-receipt.json').read_text())['pngs']
paths={r['asset_folder']+'/'+r['name'] for r in rows}
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in paths]
if dirty:raise RuntimeError('Preserve unsaved icon packages '+str(dirty))
out=[]
for row in rows:
    task=u.AssetImportTask();task.filename=row['png'];task.destination_path=row['asset_folder'];task.destination_name=row['name']
    task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
    a=u.load_asset(task.destination_path+'/'+task.destination_name)
    if not isinstance(a,u.Texture2D):raise RuntimeError('Import missing '+row['name'])
    a.srgb=True;a.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
    a.lod_group=u.TextureGroup.TEXTUREGROUP_UI;a.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    E.set_metadata_tag(a,'BowModularSource','SourceAssets/BowModular20260926/icon-authoring.json')
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    out.append(dict(name=row['name'],asset=a.get_path_name(),sha256=row['sha256']))
    (P/'icon-import-receipt.json').write_text(json.dumps(dict(saved=out,gameplay_tested=False),indent=2),encoding='utf8')
print('BOW_ICON_TEXTURES_SAVED',len(out))
