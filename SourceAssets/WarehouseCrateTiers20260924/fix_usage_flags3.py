"""v3: force modify() to mark dirty, report PIE state, save via save_loaded_asset + save_dirty_packages.

If PIE is active, editor save is blocked -> we report that instead of silently failing.
"""
import json
import os
import unreal

MAT_DIR = '/Game/Props/WarehouseCrateTiers20260924/Materials/'
DISK_DIR = r'D:\FPS3D\FPSGAME\Content\Props\WarehouseCrateTiers20260924\Materials'
NAMES = ['M_Crate_Wood', 'M_Crate_WoodDark', 'M_Crate_Stone', 'M_Crate_Iron',
         'M_Crate_IronDark', 'M_Crate_Gold', 'M_Crate_Silver', 'M_Crate_Gem']
report = {'assets': {}}
try:
    world = unreal.EditorLevelLibrary.get_editor_world() if hasattr(unreal, 'EditorLevelLibrary') else None
except Exception:
    world = None
try:
    report['pie_active'] = bool(unreal.GameEditorSubsystem and unreal.EditorPlaySettings)
except Exception:
    pass
try:
    ges = unreal.get_editor_subsystem(unreal.GameEditorSubsystem) if hasattr(unreal, 'GameEditorSubsystem') else None
    if ges:
        report['pie_playing'] = bool(ges.is_playing())
except Exception as exc:
    report['pie_probe_err'] = str(exc)[:80]

assets = []
for n in NAMES:
    path = MAT_DIR + n
    disk = os.path.join(DISK_DIR, n + '.uasset')
    before = os.path.getmtime(disk) if os.path.exists(disk) else None
    m = unreal.load_asset(path)
    if m is None:
        report['assets'][n] = 'MISSING'
        continue
    try:
        m.modify()
    except Exception as exc:
        report.setdefault('modify_err', []).append('%s:%s' % (n, str(exc)[:50]))
    m.set_editor_property('used_with_skeletal_mesh', True)
    saved = bool(unreal.EditorAssetLibrary.save_loaded_asset(m))
    after = os.path.getmtime(disk) if os.path.exists(disk) else None
    report['assets'][n] = {'now': bool(m.get_editor_property('used_with_skeletal_mesh')),
                           'save_ret': saved, 'mtime_changed': before != after}
    assets.append(m)
try:
    report['bulk_save'] = bool(unreal.EditorLoadingAndSavingUtils.save_assets(assets))
except Exception as exc:
    report['bulk_save_err'] = str(exc)[:100]
mts = {n: os.path.getmtime(os.path.join(DISK_DIR, n + '.uasset')) for n in NAMES if os.path.exists(os.path.join(DISK_DIR, n + '.uasset'))}
report['final_mtimes'] = mts
with open(r'D:\FPS3D\FPSGAME\SourceAssets\WarehouseCrateTiers20260924\probes\usage_fix3.json', 'w', encoding='utf-8') as fh:
    json.dump(report, fh, ensure_ascii=False, indent=1)
print('USAGE_FIX3_DONE', flush=True)
