"""Headless check: do the exact asset paths the code and item data use resolve?"""
import unreal as u

PATHS = [
    '/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick.S_MeleeHit_Quick',
    '/Game/Audio/WeaponHit20260916/S_GunHit.S_GunHit',
    '/Game/Weapons/AzureRunesword20260913/Sword_Hit.Sword_Hit',
    '/Game/Audio/PlayerHitFeedback20260914/S_Player_MonsterHit.S_Player_MonsterHit',
]
print('DIR_EXISTS', u.EditorAssetLibrary.does_directory_exist('/Game/Audio/WeaponHit20260916'))
for path in PATHS:
    asset = u.load_asset(path)
    duration = None
    if asset:
        try:
            duration = asset.get_editor_property('duration')
        except Exception:
            duration = 'n/a'
    print('LOAD %-70s -> %s  duration=%s' % (path, asset.get_name() if asset else 'MISSING', duration))
print('CHECK_PATHS_DONE')
