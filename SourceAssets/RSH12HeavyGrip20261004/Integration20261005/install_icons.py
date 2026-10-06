"""Publish RSH-only icon keys and save their UE UI texture copies."""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];D='/Game/Weapons/RSH12/HeavyGrip20261005/Icons'
root=P/'Content/ColdSteelData/AttachmentIcons20260913';A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Unexpected project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE prevents icon import')
mapping={'ue_rsh12_grip_body_rsh12_heavy_grip':'HeavyGrip_Framed.png','ue_rsh12_category_grip_body':'FactoryGrip_Framed.png','ue_rsh12_grip_body_false':'FactoryGrip_Framed.png'}
saved=[]
for key,file in mapping.items():
    for folder in (root,root/'FramedFirearms'):
        target=folder/(key+'.png');folder.mkdir(parents=True,exist_ok=True)
        if target.exists() and not (O/'BeforeIcons'/folder.name/target.name).exists():
            backup=O/'BeforeIcons'/folder.name/target.name;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
        shutil.copy2(O/file,target)
    task=u.AssetImportTask();task.filename=str(O/file);task.destination_path=D;task.destination_name='T_'+key;task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task]);asset=u.load_asset(D+'/T_'+key)
    if not asset:raise RuntimeError('Icon import failed '+key)
    asset.srgb=True;asset.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;asset.lod_group=u.TextureGroup.TEXTUREGROUP_UI;asset.never_stream=True
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Icon save failed '+key)
    saved.append(asset.get_path_name())
(O/'icon_receipt.json').write_text(json.dumps(dict(complete=True,saved=saved,png_keys=mapping,source='Built-in image_gen; approved model + actual factory 9_l + accepted frame',runtime_tested=False),indent=2))
print('RSH_HEAVY_GRIP_ICONS_SAVED',flush=True)
