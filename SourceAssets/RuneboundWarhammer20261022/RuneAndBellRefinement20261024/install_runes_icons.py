"""Import the new shaft masks and the exact runtime UI PNGs in the same save batch."""
import shutil
mask_folder='/Game/Weapons/MeleeRunes20260915/SurfaceV2'
for kind in ('swift_mana_rune','destruction_mana_rune'):
    name='T_Mask_'+kind
    task=u.AssetImportTask();task.filename=str(P/'Masks'/(name+'.png'))
    task.destination_path=mask_folder;task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=False
    A.import_asset_tasks([task])
    texture=u.load_asset(mask_folder+'/'+name)
    if not texture:raise RuntimeError('Cannot import '+name)
    texture.set_editor_property('srgb',False)
    texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON)
    texture.set_editor_property('address_x',u.TextureAddress.TA_CLAMP)
    texture.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
    save(texture)
icon_folder='/Game/Weapons/RuneboundWarhammer20261022/RuneIconsV3'
for source in sorted((P/'Icons').glob('*.png')):
    asset_path=icon_folder+'/'+source.stem
    if any(str(pkg.get_name())==asset_path for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve dirty icon '+asset_path)
    task=u.AssetImportTask();task.filename=str(source)
    task.destination_path=icon_folder;task.destination_name=source.stem
    task.automated=True;task.save=False;task.replace_existing=False
    A.import_asset_tasks([task])
    icon=u.load_asset(asset_path)
    if not icon:raise RuntimeError('Cannot import '+asset_path)
    icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    icon.set_editor_property('srgb',True);icon.set_editor_property('never_stream',True)
    icon.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    save(icon)
receipt.update(complete=True,rune_masks=2,framed_icons=len(list((P/'Icons').glob('*.png'))),tested=False)
record()
