"""Save UE copies of this weapon's production UI textures."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
rows=json.loads((P/'catalog_receipt.json').read_text(encoding='utf-8'))['icons']
L=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();receipt=[]
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world() is not None:raise RuntimeError('Finish PIE before UI asset import.')
for relative in rows:
    file=ROOT/relative;folder='/Game/'+file.parent.relative_to(ROOT/'Content').as_posix()
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=file.stem
    task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
    tex=u.load_asset(folder+'/'+file.stem)
    if not tex or not task.imported_object_paths:raise RuntimeError('Icon import failed: '+str(file))
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);tex.set_editor_property('srgb',True)
    if not L.save_loaded_asset(tex,False):raise RuntimeError('Icon save failed: '+tex.get_path_name())
    receipt.append({'png':relative,'asset':tex.get_path_name(),'saved':True})
(P/'icon_import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('HIGHLAND_UI_TEXTURES_IMPORTED '+str(len(receipt)))
