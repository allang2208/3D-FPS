"""Save the shared grayscale blessed emitter UI texture in the current project."""
import json
from pathlib import Path
import unreal as u

root=Path(__file__).resolve().parents[3]
source=root/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/tactical_blessed_laser.png'
dest='/Game/Weapons/TacticalDevices20260913/BlessedLaser20261006/Icons'
name='T_BlessedLaserIcon'
task=u.AssetImportTask()
task.filename=str(source)
task.destination_path=dest
task.destination_name=name
task.automated=True
task.replace_existing=True
task.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture=u.load_asset(dest+'/'+name)
if texture is None:raise RuntimeError('Blessed laser icon import failed')
texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
texture.set_editor_property('srgb',True)
texture.set_editor_property('never_stream',True)
if not u.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()],False):
    raise RuntimeError('Blessed laser icon save failed')
receipt={'source':str(source),'texture':texture.get_path_name(),'saved':True,'game_tested':False}
(root/'SourceAssets/BlessedLaser20261006/Model/icon-import-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('BLESSED_EMITTER_ICON_SAVED '+texture.get_path_name())
