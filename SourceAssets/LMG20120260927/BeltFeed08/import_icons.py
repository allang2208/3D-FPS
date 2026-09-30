import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;R=O.parents[2];P='/Game/ColdSteelData/AttachmentIcons20260913'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();receipt=[]
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active')
for job in json.loads((O/'icon_authoring.json').read_text()):
 key=job['key'];dest=R/'Content/ColdSteelData/AttachmentIcons20260913'/(key+'.png');shutil.copy2(job['file'],dest)
 t=u.AssetImportTask();t.filename=str(dest);t.destination_path=P;t.destination_name=key;t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t])
 tex=u.load_asset(P+'/'+key)
 if not tex or not t.imported_object_paths:raise RuntimeError('Icon import failed '+key)
 tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
 tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
 tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
 if not E.save_loaded_asset(tex,False):raise RuntimeError('Icon save failed '+key)
 receipt.append({'key':key,'png':str(dest),'asset':tex.get_path_name(),'saved':True})
(O/'icon_import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print('201_FEED_ICONS_SAVED',len(receipt))
