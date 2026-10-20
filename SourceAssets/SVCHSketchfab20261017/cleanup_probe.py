import unreal as u
E=u.EditorAssetLibrary
for p in ('/Game/Weapons/SVCH/ProbeSlotOrder/SK_Probe','/Game/Weapons/SVCH/ProbeSlotOrder'):
    if E.does_asset_exist(p):
        print('DEL', p, E.delete_asset(p))
    elif E.does_directory_exist(p):
        print('DELDIR', p, E.delete_directory(p))
print('REMAIN', E.does_directory_exist('/Game/Weapons/SVCH/ProbeSlotOrder'))
