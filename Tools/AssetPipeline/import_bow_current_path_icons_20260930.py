import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
source = root / 'Content/ColdSteelData/AttachmentIcons20260913'
destination = '/Game/ColdSteelData/AttachmentIcons20260913'
tasks = []
manifest = json.loads((root / 'SourceAssets/BowFramedIcons20260930/manifest.json').read_text(encoding='utf-8-sig'))
for key in sorted(key for group in manifest['groups'] for key in group):
    png = source / (key + '.png')
    task = unreal.AssetImportTask()
    task.filename = str(png)
    task.destination_path = destination
    task.destination_name = png.stem
    task.automated = True
    task.replace_existing = True
    task.save = True
    tasks.append(task)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
if any(not task.imported_object_paths for task in tasks):
    raise RuntimeError('One or more bow icon imports failed')
saved = []
for task in tasks:
    for path in task.imported_object_paths:
        texture = unreal.load_asset(path)
        if isinstance(texture, unreal.Texture2D):
            texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
            texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_EDITOR_ICON)
            texture.set_editor_property('never_stream', True)
            texture.set_editor_property('srgb', True)
            if not unreal.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()], False):
                raise RuntimeError("Could not save " + path)
            saved.append(path)
(root / 'SourceAssets/BowFramedIcons20260930/import_current_path_result.json').write_text(json.dumps(saved, indent=2), encoding='utf-8')
print('FRAMED_BOW_ICONS_SAVED', len(saved))
