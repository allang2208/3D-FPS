"""Finish saving this batch's mask after the authorized PIE stop."""
import unreal as u
asset=u.load_asset('/Game/Weapons/M24/CarbonBolt20261029/Textures/T_M24_CarbonWeaveMask')
if not asset or not u.EditorAssetLibrary.save_loaded_asset(asset,False):
    raise RuntimeError('Carbon mask save remains blocked')
print('M24_CARBON_MASK_SAVED')
