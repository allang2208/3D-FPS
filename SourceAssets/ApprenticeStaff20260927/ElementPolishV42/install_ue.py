"""Save four material-only elemental revisions; no meshes, mounts or VFX edits."""
import json
import runpy
import shutil
import traceback
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
BASE = '/Game/Weapons/ApprenticeStaff20260927'
DEST = BASE+'/ElementPolishV42'
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
recipe = runpy.run_path(str(ROOT/'ue_material.py'))
heads = recipe['P']['heads']
paths = {kind:recipe['material_path'](kind) for kind in heads}
report = dict(revision=42,complete=False,active=False,saved_assets=[],installed=[],backups=[],
              geometry_changed=False,white_quartz_changed=False,mounts_changed=False,
              opacity_or_color_changed=False,emission_changed=False,storm_animation_changed=False,
              cpp_changed=False,global_renderer_changed=False,runtime_tested=False,rendered=False)


def record():
    (ROOT/'install-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


def compile_save(material):
    errors = L.recompile_material(material)
    if errors:
        raise RuntimeError('Elemental surface compile failed '+material.get_path_name()+': '+str(errors))
    if not E.save_loaded_asset(material,False):
        raise RuntimeError('Cannot save '+material.get_path_name())
    report['saved_assets'].append(material.get_path_name())
    record()


def install():
    if not json.loads((ROOT/'author-receipt.json').read_text(encoding='utf-8'))['complete']:
        raise RuntimeError('Editable source has not been saved')
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if editor and editor.is_in_play_in_editor():
            raise RuntimeError('End PIE before material installation; no targets changed.')
    dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    conflicts=[p for p in dirty if p in paths.values() or p.startswith(DEST+'/')]
    if conflicts:
        raise RuntimeError('Unsaved elemental targets preserved: '+', '.join(conflicts))
    materials={}
    for kind,path in paths.items():
        material=u.load_asset(path)
        head=u.load_asset(BASE+'/Meshes/SM_Staff_head_crystal_'+heads[kind]['id'])
        if not material or not head or not any(s.material_interface==material for s in head.static_materials):
            raise RuntimeError('Current '+kind+' material binding differs; existing assets preserved')
        materials[kind]=material
    for kind,path in paths.items():
        relative=Path(path.removeprefix('/Game/')+'.uasset')
        before=ROOT/'Before/Content'/relative
        if not before.exists():
            before.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(PROJECT/'Content'/relative,before)
        backup_path=DEST+'/Before/M_'+kind
        if not E.does_asset_exist(backup_path):
            backup=E.duplicate_asset(path,backup_path)
            if not backup or not E.save_loaded_asset(backup,False):
                raise RuntimeError('Cannot back up '+path)
        report['backups'].append(dict(target=path,copy=backup_path,disk=str(before)))
        record()
        candidate_path=DEST+'/Materials/M_ElementPolish_'+kind+'_V42'
        candidate=u.load_asset(candidate_path) or E.duplicate_asset(backup_path,candidate_path)
        if not candidate:
            raise RuntimeError('Cannot create '+candidate_path)
        recipe['apply_surface'](candidate,kind)
        compile_save(candidate)
    for kind,material in materials.items():
        recipe['apply_surface'](material,kind)
        compile_save(material)
        report['installed'].append(material.get_path_name())
        record()
    report.update(complete=True,active=True)
    record()
    print('STAFF_ELEMENT_POLISH_V42_SAVED heads=4 materials=8 geometry_changed=false tested=false rendered=false',flush=True)


try:
    install()
except Exception:
    report['error']=traceback.format_exc()
    record()
    raise
