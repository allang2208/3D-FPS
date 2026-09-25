"""Probe whether the asset-registry metadata tag API actually persists."""
import unreal as u

asset = '/Game/Weapons/AKMIntegration/SovietFab/ReloadPolish/base/A_AKM_reload'
anim = u.load_asset(asset)
E = u.EditorAssetLibrary
print('BEFORE', repr(E.get_metadata_tag(anim, 'GripRefinement2')), flush=True)
ok = E.set_metadata_tag(anim, 'GripRefinement2', 'AKM/A762 reload thumb extended upward 2026-09-25')
print('SET returned', ok, 'read-back', repr(E.get_metadata_tag(anim, 'GripRefinement2')), flush=True)
saved = E.save_loaded_asset(anim, False)
print('SAVE returned', saved, 'read-back', repr(E.get_metadata_tag(anim, 'GripRefinement2')), flush=True)
ok2 = E.set_metadata_tag(anim, 'GripProbe', 'probe')
print('SET2 returned', ok2, 'read-back', repr(E.get_metadata_tag(anim, 'GripProbe')), flush=True)
print('TAG_PROBE_OK', flush=True)
