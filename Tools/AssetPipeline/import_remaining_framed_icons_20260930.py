"""Import and save only the deployed remaining modification icons."""
import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
work = root / 'SourceAssets/RemainingFramedIcons20260930'
receipt = json.loads((work / 'deploy_result.json').read_text(encoding='utf-8'))
tasks = []
for item in receipt:
    png = root / item['destination']
    task = unreal.AssetImportTask()
    task.filename = str(png)
    task.destination_path = '/Game/' + str(png.parent.relative_to(root / 'Content')).replace('\\', '/')
    task.destination_name = png.stem
    task.automated = True
    task.replace_existing = True
    task.save = True
    tasks.append(task)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
if any(not task.imported_object_paths for task in tasks):
    raise RuntimeError('One or more remaining icon imports failed')
saved = []
for task in tasks:
    for path in task.imported_object_paths:
        texture = unreal.load_asset(path)
        if not isinstance(texture, unreal.Texture2D):
            raise RuntimeError('Expected Texture2D: ' + path)
        texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
        texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_EDITOR_ICON)
        texture.set_editor_property('never_stream', True)
        texture.set_editor_property('srgb', True)
        if not unreal.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()], False):
            raise RuntimeError('Could not save ' + path)
        saved.append(path)
(work / 'import_result.json').write_text(json.dumps(saved, indent=2), encoding='utf-8')
print('REMAINING_FRAMED_ICONS_SAVED', len(saved))
