"""In-editor fix v2: set skeletal usage flag AND force-save via save_loaded_asset (path-based
save_asset silently no-op'd: mtimes unchanged). Reports mtime before/after as persistence proof.
"""
import json
import os
import unreal

MAT_DIR = '/Game/Props/WarehouseCrateTiers20260924/Materials/'
DISK_DIR = r'D:\FPS3D\FPSGAME\Content\Props\WarehouseCrateTiers20260924\Materials'
NAMES = ['M_Crate_Wood', 'M_Crate_WoodDark', 'M_Crate_Stone', 'M_Crate_Iron',
         'M_Crate_IronDark', 'M_Crate_Gold', 'M_Crate_Silver', 'M_Crate_Gem']
report = {}
for n in NAMES:
    path = MAT_DIR + n
    disk = os.path.join(DISK_DIR, n + '.uasset')
    before_mtime = os.path.getmtime(disk) if os.path.exists(disk) else None
    m = unreal.load_asset(path)
    if m is None:
        report[n] = 'MISSING'
        continue
    was = bool(m.get_editor_property('used_with_skeletal_mesh'))
    if not was:
        try:
            m.modify()
        except Exception as exc:
            report.setdefault('modify_err', []).append('%s: %s' % (n, str(exc)[:60]))
        m.set_editor_property('used_with_skeletal_mesh', True)
    saved = bool(unreal.EditorAssetLibrary.save_loaded_asset(m))
    now = bool(m.get_editor_property('used_with_skeletal_mesh'))
    after_mtime = os.path.getmtime(disk) if os.path.exists(disk) else None
    report[n] = {'was': was, 'now': now, 'save_ret': saved,
                 'mtime_changed': bool(before_mtime != after_mtime),
                 'after_mtime': after_mtime}
all_ok = all(isinstance(v, dict) and v['now'] and v['mtime_changed'] for v in report.values())
report['ALL_OK'] = all_ok
with open(r'D:\FPS3D\FPSGAME\SourceAssets\WarehouseCrateTiers20260924\probes\usage_fix2.json', 'w', encoding='utf-8') as fh:
    json.dump(report, fh, ensure_ascii=False, indent=1)
print('USAGE_FIX2_DONE', flush=True)
