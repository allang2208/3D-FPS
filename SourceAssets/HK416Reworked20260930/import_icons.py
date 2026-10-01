"""Publish and save production HK416 UI textures."""
import unreal as u,json,shutil,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];ROOT='/Game/Weapons/HK416/Reworked20260930'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
icons=json.loads((O/'icon_render_receipt.json').read_text());report={'saved':[],'icons':{},'runtime_tested':False}
for key,entry in icons.items():
    source=Path(entry['file']);equipment=key=='ue_hk416';folder='/Game/ColdSteelData/Icons' if equipment else ROOT+'/Icons'
    dest=P/'Content/ColdSteelData'/('Icons' if equipment else 'AttachmentIcons20260913')/(key+'.png');shutil.copy2(source,dest)
    task=u.AssetImportTask();task.filename=str(dest);task.destination_path=folder;task.destination_name=key
    task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);tex=u.load_asset(folder+'/'+key)
    if not tex:raise RuntimeError('Icon import failed '+key)
    tex.srgb=True;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    E.set_metadata_tag(tex,'HK416IconSource',str(source));E.set_metadata_tag(tex,'Attribution','HK416 Full ReWorked / MojoLeeDa / CC BY 4.0; modified for FPSGAME')
    # Save only the authored editor asset package, using the same package writer
    # as mesh/material production; no map or PIE world packages are included.
    if not u.EditorLoadingAndSavingUtils.save_packages([tex.get_outermost()],False):raise RuntimeError('Icon save failed '+key)
    report['saved'].append(tex.get_path_name());report['icons'][key]={'asset':tex.get_path_name(),'png':str(dest),'size':entry['size'],'grayscale':entry['grayscale'],'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    (O/'icon_import_receipt.json').write_text(json.dumps(report,indent=2))
report['status']='hk416_icons_published_imported_and_saved';(O/'icon_import_receipt.json').write_text(json.dumps(report,indent=2));print('HK416_ICONS_IMPORTED_AND_SAVED',len(icons))
