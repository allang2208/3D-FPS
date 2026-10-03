"""Restore TangDao blade-II overlays without changing the refined PBR assets."""
import unreal as u, json, shutil
from pathlib import Path
P = Path(__file__).parent
ROOT = P.parents[3]
if Path(u.Paths.project_dir()).resolve() != ROOT:
    raise RuntimeError('TangDao rune repair must run in FPSGAME')
commandlet = '-run=' in u.SystemLibrary.get_command_line().lower()
catalog = json.loads((ROOT/'Content/ColdSteelData/tang-dao-modules.json').read_text(encoding='utf-8-sig'))
paths = sorted({row['mesh'].split('.')[0] for row in catalog['slots']['blade_1'].values()})
if any(not path.startswith('/Game/Weapons/TangDao20261002/Meshes/SM_TangDao_Blade_') for path in paths):
    raise RuntimeError('Retained another blade revision; apply its overlay policy explicitly')
dirty = [] if commandlet else [pkg.get_name() for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if pkg.get_name() in paths]
if dirty:
    raise RuntimeError('Retained unsaved TangDao blade changes: '+str(dirty))
receipt = {'revision': 'TangDaoBladeRuneOverlay20261002', 'assets': [], 'complete': False,
           'runtime_tested': False, 'geometry_changed': False, 'pbr_materials_changed': False,
           'cause': 'Nanite blade rendering skips the existing translucent rune overlay',
           'runes': ['resonance_rune', 'erosion_rune', 'conduction_rune']}
for path in paths:
    mesh = u.load_asset(path)
    if not mesh:
        raise RuntimeError('Missing TangDao blade '+path)
    source = ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    backup = P/'Before'/source.relative_to(ROOT)
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(source, backup)
    settings = mesh.get_editor_property('nanite_settings')
    before = settings.enabled
    settings.enabled = False
    mesh.set_editor_property('nanite_settings', settings)
    u.EditorAssetLibrary.set_metadata_tag(mesh, 'TangDaoRuneOverlayRevision', receipt['revision'])
    if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()], False):
        raise RuntimeError('Could not save overlay-compatible blade '+path)
    receipt['assets'].append({'asset': mesh.get_path_name(), 'nanite_before': before, 'nanite_after': False,
                             'geometry_and_material_slots_preserved': True})
    (P/'import_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    print('TANGDAO_RUNE_BLADE_SAVED', mesh.get_path_name(), flush=True)
receipt['complete'] = True
(P/'import_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('TANGDAO_RUNE_OVERLAY_REPAIR_SAVED', json.dumps(receipt, ensure_ascii=False), flush=True)
