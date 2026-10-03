import unreal as u
for variant in ('Standard','LongGrip'):
    path='/Game/Weapons/SwordUppercut20261003/'+variant+'/A_Sword_UppercutV1_'+variant
    asset=u.load_asset(path)
    u.log(str(dict(asset=path,source=u.EditorAssetLibrary.get_metadata_tag(asset,'SwordUppercut.AuthorSource'),
                   revision=u.EditorAssetLibrary.get_metadata_tag(asset,'SwordUppercut.Revision'))))
