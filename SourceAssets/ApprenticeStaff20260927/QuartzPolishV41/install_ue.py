"""Save polished default quartz at the existing world and UI material paths."""
import json
import runpy
import shutil
import traceback
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
BASE = '/Game/Weapons/ApprenticeStaff20260927'
DEST = BASE+'/QuartzPolishV41'
WORLD = BASE+'/QuartzAimV22/Materials/M_Staff_QuartzDenseV22'
PREVIEW = '/Game/UI/GunsmithWorkbench/M_StaffQuartzPreviewV23'
E = u.EditorAssetLibrary
report = dict(revision=41,complete=False,active=False,saved_assets=[],installed=[],backups=[],
              basis='V36 before wear',geometry_changed=False,optical_parameters_changed=False,
              global_renderer_settings_changed=False,element_heads_changed=False,cpp_changed=False,
              lamp_changed=False,runtime_tested=False,rendered=False)


def record():
    (ROOT/'install-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


def install():
    if not json.loads((ROOT/'author-receipt.json').read_text(encoding='utf-8'))['complete']:
        raise RuntimeError('Polished material authoring has not completed')
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    conflicts = [p for p in dirty if p in (WORLD,PREVIEW) or p.startswith(DEST+'/')]
    if conflicts:
        raise RuntimeError('Unsaved quartz target preserved: '+', '.join(conflicts))
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
        if editor and editor.is_in_play_in_editor():
            raise RuntimeError('PIE is active; finish play before material installation.')
    for path,name in ((WORLD,'WorldMaterial'),(PREVIEW,'PreviewMaterial')):
        if not u.load_asset(path):
            raise RuntimeError('Missing active quartz '+path)
        relative = Path(path.removeprefix('/Game/')+'.uasset')
        before = ROOT/'Before/Content'/relative
        if not before.exists():
            before.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(PROJECT/'Content'/relative,before)
        backup_path = DEST+'/Before/'+name
        if not E.does_asset_exist(backup_path):
            backup = E.duplicate_asset(path,backup_path)
            if not backup or not E.save_loaded_asset(backup,False):
                raise RuntimeError('Cannot preserve '+path)
        report['backups'].append(dict(target=path,copy=backup_path,disk=str(before)))
        record()
    head = u.load_asset(BASE+'/Meshes/SM_Staff_head_crystal_false')
    if not head or not any(s.material_interface and s.material_interface.get_path_name().split('.')[0] == WORLD
                           for s in head.static_materials):
        raise RuntimeError('Default head uses another material; target changes stopped')
    build = runpy.run_path(str(ROOT/'ue_material.py'))['build_quartz_material']
    for preview in (False,True):
        asset = build(rebuild=True,preview=preview,candidate=True)
        report['saved_assets'].append(asset.get_path_name())
        record()
    for preview in (False,True):
        asset = build(rebuild=True,preview=preview)
        report['saved_assets'].append(asset.get_path_name())
        report['installed'].append(asset.get_path_name())
        record()
    report.update(complete=True,active=True)
    record()
    # V40 was rejected and archived. Rebuilding the active material must not
    # require or modify an obsolete revision's local installation receipt.
    print('STAFF_QUARTZ_V41_SAVED materials=4 wear_removed=true geometry_changed=false tested=false rendered=false',flush=True)


try:
    install()
except Exception:
    report['error'] = traceback.format_exc()
    record()
    raise
