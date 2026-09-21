"""Archive superseded witch packages after checking their live dependency boundary.

Run through the project's mutex bridge. Default is a read-only archive plan;
set WITCH_ARCHIVE_EXECUTE=True in the execution namespace to archive the plan.
Current V06/V07, Quinn, props, materials and source skeleton dependencies remain.
"""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME').resolve()
T = P / 'trash/witch-retired-20260921'
O = P / 'Docs/AssetArchives'
if Path(u.Paths.project_dir()).resolve() != P:
    raise RuntimeError('Wrong project; no changes made')
ar = u.AssetRegistryHelpers.get_asset_registry()
prefix = '/Game/Monsters/WitchMeshy/'
retired = ('Animations/', 'PreviousCloudGripV02/', 'PreviousLocalRetargetV01/',
           'RobeGaitV03/', 'LayeredV04/')
assets = ar.get_assets_by_path(prefix.rstrip('/'), recursive=True)
byname = {str(a.package_name): a for a in assets
          if str(a.package_name).removeprefix(prefix).startswith(retired)}
opts = u.AssetRegistryDependencyOptions(include_soft_package_references=True,
    include_hard_package_references=True, include_searchable_names=False,
    include_soft_management_references=True, include_hard_management_references=True)
refs = {p: set(map(str, ar.get_referencers(p, opts))) for p in byname}
keep = {p for p in byname if refs[p] - byname.keys() or byname[p].is_asset_loaded()}
# Existing authoring scripts still use this source mesh and native retarget setup.
keep |= {p for p in byname if p == prefix+'PreviousCloudGripV02/SK_Witch_Meshy'
         or p.startswith(prefix+'LayeredV04/Rig/')
         or p.startswith(prefix+'LayeredV04/RetargetedRaw/')}
while True:
    expanded = keep | {p for p in byname if refs[p] & keep}
    if expanded == keep:
        break
    keep = expanded
plan = {'retained': [{'package': p, 'loaded': byname[p].is_asset_loaded(),
                     'referencers': sorted(refs[p])} for p in sorted(keep)],
        'archive': sorted(byname.keys() - keep),
        'scope': 'Superseded packages only; current ordinary Witch and Quinn retained'}
O.mkdir(parents=True, exist_ok=True)
(P/'Saved/Witch-retired-assets-plan.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
if not globals().get('WITCH_ARCHIVE_EXECUTE', False):
    print(json.dumps(plan))
else:
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('PIE is running; no packages archived')
    dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty & set(plan['archive']):
        raise RuntimeError('A retired target has unsaved changes; preserved')
    receipt = O/'witch-retired-assets-20260921.json'
    rows = json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else []
    pending = []
    for p in plan['archive']:
        src = (P/'Content'/(p.removeprefix('/Game/')+'.uasset')).resolve()
        dst = (T/src.relative_to(P)).resolve()
        assert src.is_relative_to((P/'Content/Monsters/WitchMeshy').resolve())
        assert dst.is_relative_to(T.resolve())
        if dst.exists() or byname[p].is_asset_loaded():
            raise RuntimeError('Archive conflict; preserved '+p)
        sha = hashlib.sha256(src.read_bytes()).hexdigest()
        size = src.stat().st_size
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if dst.stat().st_size != size or hashlib.sha256(dst.read_bytes()).hexdigest() != sha:
            raise RuntimeError('Archive copy differs; source preserved '+p)
        pending.append({'source': src.relative_to(P).as_posix(),
                     'destination': dst.relative_to(P).as_posix(), 'bytes': size, 'sha256': sha,
                     'reason': 'Superseded witch experiment, no retained package referencers',
                     'replacement': 'OriginalRobeV05 (V06 contents), SpellSupportV07; WitchFoundation retained'})
    # Delete the self-contained retired set together; per-asset deletion can load
    # or alter another retired package before its original bytes are archived.
    loaded = [u.load_asset(p) for p in plan['archive']]
    if any(a is None for a in loaded):
        raise RuntimeError('Could not load a retired package; archive copies retained')
    deleted = not loaded or u.EditorAssetLibrary.delete_loaded_assets(loaded)
    rows.extend(row for row in pending if not (P/row['source']).exists())
    receipt.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    if not deleted or any((P/row['source']).exists() for row in pending):
        raise RuntimeError('Editor retained some source packages; consult archive receipt')
    print(json.dumps({'archived': len(rows), 'retained_dependencies': plan['retained']}))
