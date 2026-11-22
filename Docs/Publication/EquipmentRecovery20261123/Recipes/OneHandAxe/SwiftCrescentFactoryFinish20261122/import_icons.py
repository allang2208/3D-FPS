"""Bake UI texture packages for the two shipped icon layouts."""
import json
import os
from pathlib import Path
import unreal as u

art=Path(__file__).resolve().parent
batch=Path(os.environ['CRESCENT_BATCH'])
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve() != (batch/'Host').resolve():
    raise RuntimeError('Use the isolated authoring project')
outputs=[]
for folder,name in [('AttachmentIcons20260913','blade_1_axe_swift_crescent'),('Icons','ue_tactical_hatchet_axe_swift_crescent')]:
    pkg='/Game/ColdSteelData/'+folder
    file=art/'Icons'/(name+'.png')
    task=u.AssetImportTask()
    task.set_editor_properties(dict(filename=str(file),destination_name=name,destination_path=pkg,
                                   automated=True,replace_existing=True,save=False))
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    asset=u.EditorAssetLibrary.load_asset(pkg+'/'+name)
    if not task.imported_object_paths or not isinstance(asset,u.Texture2D):
        raise RuntimeError('Cannot import '+name)
    asset.set_editor_properties(dict(srgb=True,lod_group=u.TextureGroup.TEXTUREGROUP_UI,
        compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,never_stream=True,
        mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,max_texture_size=1024))
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Cannot save '+name)
    outputs.append(asset.get_path_name())
(batch/'authored-icons.json').write_text(json.dumps(outputs,indent=2),encoding='utf8')
