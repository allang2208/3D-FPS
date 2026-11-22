"""Save the in-game catalog's generated artwork as a UI texture."""
from pathlib import Path
import unreal as u

project = Path(u.Paths.project_dir()).resolve()
name = 'ue_forged_steel_greatsword'
destination = '/Game/ColdSteelData/Icons'
source = project / 'Content/ColdSteelData/Icons' / (name + '.png')
task = u.AssetImportTask()
task.filename = str(source)
task.destination_path = destination
task.destination_name = name
task.automated = True
task.replace_existing = True
task.save = False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture = u.load_asset(destination + '/' + name)
if not texture:
    raise RuntimeError('Failed to import inventory icon')
texture.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_UI)
texture.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_EDITOR_ICON)
texture.set_editor_property('srgb', True)
texture.set_editor_property('never_stream', True)
if not u.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()], False):
    raise RuntimeError('Could not save ' + texture.get_path_name())
print('FORGED_STEEL_GREATSWORD_ICON_SAVED ' + texture.get_path_name(), flush=True)
