"""Publish the production PNGs and save their existing UE UI texture assets."""
import unreal as u,json,shutil,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];S=O.parent/'G18Integration20260929'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
ROOT='/Game/Weapons/G18/Integrated20260929';icons=json.loads((O/'render_receipt.json').read_text())
report={'saved':[],'icons':{},'runtime_tested':False,'interactive_editor_started':False}

def before(file):
    target=O/'Before'/file.relative_to(P);target.parent.mkdir(parents=True,exist_ok=True)
    if file.exists() and not target.exists():shutil.copy2(file,target)

for key,entry in icons.items():
    source=Path(entry['file']);equipment=key=='ue_g18'
    folder='/Game/ColdSteelData/Icons' if equipment else ROOT+'/Icons'
    dest=P/'Content/ColdSteelData'/('Icons' if equipment else 'AttachmentIcons20260913')/(key+'.png')
    package=P/'Content'/folder.removeprefix('/Game/')/(key+'.uasset')
    before(dest);before(package);shutil.copy2(source,dest)
    task=u.AssetImportTask();task.filename=str(dest);task.destination_path=folder;task.destination_name=key
    task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task]);texture=u.load_asset(folder+'/'+key)
    if not texture:raise RuntimeError('Icon import failed '+key)
    texture.srgb=True;texture.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
    texture.lod_group=u.TextureGroup.TEXTUREGROUP_UI;texture.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    E.set_metadata_tag(texture,'G18IconProduction','20260930: 1024 transparent; actual single parts; grayscale modifications; original-PBR equipment')
    E.set_metadata_tag(texture,'G18IconSource',str(source))
    if not E.save_loaded_asset(texture,only_if_is_dirty=False):raise RuntimeError('Could not save '+key)
    report['saved'].append(texture.get_path_name())
    report['icons'][key]={'asset':texture.get_path_name(),'png':str(dest),'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'size':entry['size'],'grayscale':entry['grayscale']}
    (O/'import_receipt.json').write_text(json.dumps(report,indent=2))

# The original publication manifest now names this production recipe.
manifest={'production_recipe':str(O/'author_icons.py'),'production_receipt':str(O/'render_receipt.json'),
    'catalog':str(P/'Content/ColdSteelData/Icons/ue_g18.png'),
    'modification_directory':str(P/'Content/ColdSteelData/AttachmentIcons20260913'),
    'method':'1024 RGBA production renders; original G18 PBR equipment; current single-part geometry and grayscale modification palette',
    'equipment_icons':1,'modification_icons':len(icons)-1,'runtime_tested':False}
(S/'icons.json').write_text(json.dumps(manifest,indent=2))
report['status']='g18_final_icons_published_imported_and_saved'
(O/'import_receipt.json').write_text(json.dumps(report,indent=2));print('G18_FINAL_ICONS_SAVED',len(icons),flush=True)
