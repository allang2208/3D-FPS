"""Import and save only the Elemental Arrow UI textures; existing VFX are reused."""
from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parents[2]
saved=[]
for element in ('fire','ice','lightning'):
    name=f'elemental_arrow_{element}'
    task=u.AssetImportTask()
    task.filename=str(ROOT/'Content/ColdSteelData/Skills'/f'{name}.png')
    task.destination_path='/Game/ColdSteelData/Skills';task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture=u.load_asset(task.destination_path+'/'+name)
    if not task.imported_object_paths or not isinstance(texture,u.Texture2D):raise RuntimeError('Import failed: '+name)
    texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('never_stream',True);texture.set_editor_property('srgb',True)
    texture.set_editor_property('max_texture_size',512)
    if not u.EditorAssetLibrary.save_loaded_asset(texture,False):raise RuntimeError('Save failed: '+name)
    saved.append({'element':element,'asset':texture.get_path_name(),'saved':True})
out=ROOT/'Saved/ElementalArrow20261027';out.mkdir(parents=True,exist_ok=True)
(out/'asset-receipt.json').write_text(json.dumps({'icons':saved,'vfx':'existing assets reused without modification','runtime_tested':False},indent=2),encoding='utf-8')
print('ELEMENTAL_ARROW_ICONS_SAVED '+str(len(saved)))
