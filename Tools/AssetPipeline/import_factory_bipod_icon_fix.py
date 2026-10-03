from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
destination = '/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
for key in ['ue_lmg201_bipod_false', 'ue_lmg201_category_bipod']:
    task = unreal.AssetImportTask()
    task.filename = str(root / 'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms' / (key + '.png'))
    task.destination_path = destination
    task.destination_name = key
    task.automated = True
    task.replace_existing = True
    task.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture = unreal.load_asset(destination + '/' + key)
    texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('never_stream', True)
    texture.set_editor_property('srgb', True)
    saved = unreal.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()], False)
    print('FACTORY_BIPOD_ICON_SAVED', key, saved)
