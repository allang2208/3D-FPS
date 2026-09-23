"""Import production option/category PNGs into the existing UI texture directory."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;D='/Game/ColdSteelData/AttachmentIcons20260913'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();receipt={}
records=json.loads((O/'icons.json').read_text())
for key,info in records.items():
 t=u.AssetImportTask();t.filename=info['output'];t.destination_path=D;t.destination_name=key;t.automated=True;t.replace_existing=True;t.save=False
 A.import_asset_tasks([t]);tex=u.load_asset(D+'/'+key)
 if not tex or not t.imported_object_paths:raise RuntimeError('SVD option icon import '+key)
 tex.srgb=True;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
 if not E.save_loaded_asset(tex,False):raise RuntimeError('SVD option icon save '+key)
 receipt[key]={'asset':tex.get_path_name(),'saved':True}
 (O/'icons_import.json').write_text(json.dumps(receipt,indent=2))
u.log('SVD_ATTACH_ICONS_IMPORTED '+str(len(receipt)))
