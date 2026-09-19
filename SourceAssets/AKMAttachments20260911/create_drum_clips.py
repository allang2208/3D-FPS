import unreal as u
P='/Game/Weapons/AKMIntegration/SovietFab/Attachments'
for c in ['reload','reload_empty']:
 d=P+'/A_AKM_drum_'+c
 if not u.EditorAssetLibrary.does_asset_exist(d):assert u.EditorAssetLibrary.duplicate_asset('/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_'+c,d)
 assert u.EditorAssetLibrary.save_asset(d,only_if_is_dirty=False)
u.log('AKM_DRUM_CLIPS_PASS')
