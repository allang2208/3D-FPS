import unreal as u
for variant,preview in [('Standard',False),('LongGrip',False),('Standard',True)]:
    target='/Game/Weapons/SwordUppercut20261003/'+variant+'/A_Sword_UppercutV1_'+variant+('_PreviewLoop' if preview else '')
    asset=u.load_asset(target)
    imported=asset.get_editor_property('asset_import_data')
    print(dict(asset=target,import_file=imported.get_first_filename() if imported else None,
               seconds=asset.get_editor_property('sequence_length')))
