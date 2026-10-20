"""Report editor play state and whether the SVCh packages are loaded.

Read-only. Used to decide whether an offline asset import may run now.
"""
import json

import unreal as u

out = {'stage': 'state'}
try:
    lev = u.get_editor_subsystem(u.LevelEditorSubsystem)
    out['pie_running'] = bool(lev and lev.is_in_play_in_editor())
except Exception as e:
    out['pie_running'] = None
    out['pie_error'] = str(e)

dirty = u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
out['dirty_svch'] = sorted(p.get_name() for p in dirty if 'SVCH' in p.get_name())

loaded = []
for pkg in ('/Game/Weapons/SVCH/Integrated20261017/SK_SVCH_Manny',
            '/Game/Weapons/SVCH/Integrated20261017/Materials/MI_SVCH_Selector'):
    loaded.append({'path': pkg, 'loaded': u.EditorAssetLibrary.does_asset_exist(pkg)})
out['assets'] = loaded

print('SVCH_STATE ' + json.dumps(out), flush=True)
