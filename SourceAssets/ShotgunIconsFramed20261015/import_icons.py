"""Replace only the six matching Texture2D assets and save them."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
manifest=json.loads((O/'deployment_receipt.json').read_text(encoding='utf-8'))
command=u.SystemLibrary.get_command_line().lower()
if '-run=pythonscript' not in command:
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('End PIE before importing the replacement icons')
report={'complete':False,'saved':[],'runtime_tested':False}
def record():(O/'import_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for row in manifest['icons']:
    for package in row['packages']:
        task=u.AssetImportTask();task.filename=row['final']
        task.destination_path,task.destination_name=package.rsplit('/',1)
        task.automated=True;task.replace_existing=True;task.replace_existing_settings=False;task.save=False
        task.factory=u.TextureFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        obj=u.load_asset(package)
        if not task.imported_object_paths or not isinstance(obj,u.Texture2D):raise RuntimeError('Import failed '+package)
        obj.modify()
        obj.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
        obj.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
        obj.set_editor_property('srgb',True);obj.set_editor_property('never_stream',True)
        u.EditorAssetLibrary.set_metadata_tag(obj,'Icon.SourceRecipe',str(O/'generation_prompts.json'))
        u.EditorAssetLibrary.set_metadata_tag(obj,'Icon.Revision','ShotgunFramedImagegen20261015')
        if not u.EditorAssetLibrary.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+package)
        report['saved'].append({'id':row['id'],'asset':obj.get_path_name(),'source':row['final']});record()
report['complete']=True;record()
print('SHOTGUN_FRAMED_TEXTURES_SAVED',len(report['saved']),flush=True)
