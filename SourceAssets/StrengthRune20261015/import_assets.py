"""Import the new common rune textures without modifying the existing rune materials."""
from pathlib import Path
import json,runpy,shutil
import unreal as u
P=Path(__file__).resolve().parent
ROOT=P.parents[1]
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
if '-run=' not in u.SystemLibrary.get_command_line().lower() and editor and editor.is_in_play_in_editor():
    raise RuntimeError('PIE active; defer asset import')
entries=[('T_Mask_strength_rune','/Game/Weapons/MeleeRunes20260915/SurfaceV2',False),
         ('blade_2_strength_rune','/Game/ColdSteelData/AttachmentIcons20260913',True)]
targets={folder+'/'+name for name,folder,_ in entries}
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_name() in targets:raise RuntimeError('Unsaved target: '+package.get_name())
L=u.EditorAssetLibrary
receipt={'complete':False,'saved_assets':[],'runtime_tested':False,'revision':'StrengthRune20261015'}
for name,folder,icon in entries:
    path=folder+'/'+name
    old=u.load_asset(path) if L.does_asset_exist(path) else None
    if old and L.get_metadata_tag(old,'AuthoringRevision')!='StrengthRune20261015':
        raise RuntimeError('Preserve unrelated existing target: '+path)
    task=u.AssetImportTask()
    task.set_editor_properties({'filename':str(P/(name+'.png')),'destination_path':folder,
        'destination_name':name,'automated':True,'replace_existing':True,'save':False})
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture=u.load_asset(path)
    if not texture:raise RuntimeError('Texture import failed: '+path)
    if icon:
        settings={'srgb':True,'lod_group':u.TextureGroup.TEXTUREGROUP_UI,
            'compression_settings':u.TextureCompressionSettings.TC_EDITOR_ICON,
            'mip_gen_settings':u.TextureMipGenSettings.TMGS_NO_MIPMAPS,'never_stream':True}
    else:
        donor=u.load_asset('/Game/Weapons/MeleeRunes20260915/SurfaceV2/T_Mask_haste_rune')
        if not donor:raise RuntimeError('Shared rune mask sampler source missing')
        settings={key:donor.get_editor_property(key) for key in ('compression_settings','lod_group','mip_gen_settings','filter')}
        settings.update(srgb=False,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,never_stream=False)
    # One batch avoids reconfiguring the texture while an asynchronous build starts.
    texture.set_editor_properties(settings)
    L.set_metadata_tag(texture,'AuthoringRevision','StrengthRune20261015')
    if not u.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()],False):
        raise RuntimeError('Texture save failed: '+path)
    receipt['saved_assets'].append(texture.get_path_name())
    (P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
shutil.copy2(P/'blade_2_strength_rune.png',ROOT/'Content/ColdSteelData/AttachmentIcons20260913/blade_2_strength_rune.png')
receipt['complete']=True
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
runpy.run_path(str(P/'register_rune.py'),run_name='__main__')
print('STRENGTH_RUNE_ASSETS_SAVED '+json.dumps(receipt),flush=True)
