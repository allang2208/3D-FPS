"""Save the two new mastery textures with the established UI import settings."""
from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'SourceAssets/MeleeMasteries20261019'
entries=json.loads((WORK/'manifest.json').read_text(encoding='utf-8'))['icons']
dest='/Game/ColdSteelData/Skills'
packages={dest+'/'+Path(e['file']).stem for e in entries}
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
tasks=[]
import_tasks={}
adopted=[]
for entry in entries:
    package=dest+'/'+Path(entry['file']).stem
    source=ROOT/'Content/ColdSteelData/Skills'/entry['file']
    if package in dirty:
        texture=u.load_asset(package)
        data=texture.get_editor_property('asset_import_data') if isinstance(texture,u.Texture2D) else None
        if not data or Path(data.get_first_filename()).resolve()!=source.resolve():
            raise RuntimeError('Preserve unsaved texture with different source: '+package)
        # This task owns the newly auto-imported PNG and its revised contents.
        # Import the current selected source, including the corrected blade V2.
        adopted.append(entry['id'])
    task=u.AssetImportTask()
    task.filename=str(source)
    task.destination_path=dest;task.destination_name=Path(entry['file']).stem
    task.automated=True;task.replace_existing=True;task.save=False
    tasks.append(task)
    import_tasks[entry['id']]=task
if tasks:u.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
saved=[]
for entry in entries:
    task=import_tasks.get(entry['id'])
    texture=u.load_asset(dest+'/'+Path(entry['file']).stem)
    if (task and not task.imported_object_paths) or not isinstance(texture,u.Texture2D):raise RuntimeError('Import failed: '+entry['id'])
    texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('never_stream',True)
    texture.set_editor_property('srgb',True)
    texture.set_editor_property('max_texture_size',512)
    if not u.EditorAssetLibrary.save_loaded_asset(texture,False):raise RuntimeError('Save failed: '+entry['id'])
    saved.append({'id':entry['id'],'asset':texture.get_path_name(),'saved':True,'adopted_own_auto_import':entry['id'] in adopted})
(WORK/'asset-receipt.json').write_text(json.dumps({'icons':saved,'runtime_tested':False},indent=2),encoding='utf-8')
print('MELEE_MASTERY_TEXTURES_SAVED '+str(len(saved)))
