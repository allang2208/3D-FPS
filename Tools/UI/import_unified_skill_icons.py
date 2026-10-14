"""Import the selected square skill icons and save Texture2D assets; no game run."""
import json
import os
from pathlib import Path
import unreal as u

root=Path(__file__).resolve().parents[2]
work=root/'SourceAssets/SkillIconUnified20261013'
entries=json.loads((work/'manifest.json').read_text(encoding='utf-8'))['icons']
only=os.environ.get('FPS_SKILL_ICON_IMPORT_ONLY','')
if only:entries=[entry for entry in entries if entry['id']==only]
dest='/Game/ColdSteelData/Skills'
packages={dest+'/'+Path(e['file']).stem for e in entries}
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
conflicts=packages&dirty
if conflicts:raise RuntimeError('Preserve unsaved icon assets: '+', '.join(sorted(conflicts)))

tasks=[]
for entry in entries:
    task=u.AssetImportTask()
    task.filename=str(root/'Content/ColdSteelData/Skills'/entry['file'])
    task.destination_path=dest
    task.destination_name=Path(entry['file']).stem
    task.automated=True
    task.replace_existing=True
    task.save=False
    tasks.append(task)
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
saved=[]
for entry,task in zip(entries,tasks):
    if not task.imported_object_paths:raise RuntimeError('Icon import failed: '+entry['id'])
    texture=u.load_asset(dest+'/'+Path(entry['file']).stem)
    if not isinstance(texture,u.Texture2D):raise RuntimeError('Missing Texture2D: '+entry['id'])
    texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('never_stream',True)
    texture.set_editor_property('srgb',True)
    texture.set_editor_property('max_texture_size',512)
    if not u.EditorAssetLibrary.save_loaded_asset(texture,False):raise RuntimeError('Cannot save: '+entry['id'])
    saved.append({'id':entry['id'],'asset':texture.get_path_name(),'saved':True})
    print('UNIFIED_SKILL_ICON_SAVED '+entry['id'])
receipt=work/'asset-import.json'
if only and receipt.is_file():
    previous=json.loads(receipt.read_text(encoding='utf-8'))['icons']
    saved=[entry for entry in previous if entry['id']!=only]+saved
receipt.write_text(json.dumps({'icons':saved,'game_tested':False},indent=2),encoding='utf-8')
print('UNIFIED_SKILL_ICONS_IMPORTED '+str(len(saved)))
