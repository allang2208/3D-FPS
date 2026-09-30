import json
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
source = root / 'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
destination = '/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
tasks = []
for png in sorted(source.glob('*.png')):
    task = unreal.AssetImportTask()
    task.filename = str(png)
    task.destination_path = destination
    task.destination_name = png.stem
    task.automated = True
    task.replace_existing = True
    task.save = True
    tasks.append(task)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
saved = []
for task in tasks:
    for path in task.imported_object_paths:
        texture = unreal.load_asset(path)
        if isinstance(texture, unreal.Texture2D):
            texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
            texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_EDITOR_ICON)
            texture.set_editor_property('never_stream', True)
            texture.set_editor_property('srgb', True)
            unreal.EditorAssetLibrary.save_loaded_asset(texture, only_if_is_dirty=False)
            saved.append(path)
(root / 'SourceAssets/FirearmFramedIcons20260930/import_result.json').write_text(json.dumps(saved, indent=2), encoding='utf-8')
print('FRAMED_FIREARM_ICONS_SAVED', len(saved))
