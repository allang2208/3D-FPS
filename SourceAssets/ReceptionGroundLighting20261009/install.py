"""Save a six-fixture overlay, preserving the entire existing reception lighting."""
from pathlib import Path
from datetime import datetime
import copy,hashlib,json,runpy,shutil,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
FLOW=PROJECT/'SourceAssets/DungeonFacilityFlow20261007'
R=runpy.run_path(str(ROOT/'recipe.py'))
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
save=runpy.run_path(str(PROJECT/'SourceAssets/ReceptionCoverage20261009/install.py'))['save']

def digest(data):return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def old_lights(world):
    out={}
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        label=a.get_actor_label()
        if not label.startswith(('Reception_Atrium_','Reception_Ground_','Reception_Upper_','Reception_Vestibule_')):continue
        c=a.get_component_by_class(u.LocalLightComponent)
        if not c:continue
        v=c.get_world_location();rot=c.get_world_rotation()
        out[label]=dict(position=[v.x,v.y,v.z],rotation=[rot.pitch,rot.yaw,rot.roll],
            fields={k:str(c.get_editor_property(k)) for k in ('intensity','intensity_units','attenuation_radius',
                'light_color','indirect_lighting_intensity','volumetric_scattering_intensity','cast_shadows',
                'max_draw_distance','max_distance_fade_range','light_function_material')})
    return out

def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if ed.get_game_world():raise RuntimeError('Preserve active gameplay; new saved-world actors need an idle editor')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    previous=ed.get_editor_world().get_path_name().split('.')[0] if ed.get_editor_world() else None
    (ROOT/'Receipts').mkdir(exist_ok=True)
    report=dict(stage='preparing',revision=R['REVISION'],maps=[],game_run=False,rendered=False,runtime_tested=False)
    def record():(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
    targets=[TARGET,*R['SUBJECTS']]
    for target in targets:
        relative=target.removeprefix('/Game/')
        paths=[PROJECT/'Content'/(relative+'.umap')]
        paths.extend(PROJECT/'Content'/sub/relative for sub in ('__ExternalActors__','__ExternalObjects__'))
        for path in paths:
            if not path.exists():continue
            dest=backup/path.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True)
            if path.is_dir():shutil.copytree(path,dest)
            else:shutil.copy2(path,dest)
    for path in (FLOW/'Config/catalog.json',FLOW/'Config/layout-bank-v1.json'):
        dest=backup/path.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    report['backup']=str(backup);record()
    try:
        world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
        generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
        if len(generators)!=1:raise RuntimeError('Expected one production generator')
        generator=generators[0];raw=generator.get_editor_property('module_catalog_json')
        (backup/'actual-catalog-before.json').write_text(raw,encoding='utf8')
        before=json.loads(raw);catalog=copy.deepcopy(before)
        contract=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash']
        bank=catalog['facility_flow']['layout_bank']
        if bank['contract_sha1']!=contract(catalog):raise RuntimeError('Preserve incomplete catalog authoring')
        module=next(m for m in catalog['modules'] if m['id']==R['MODULE'])
        original=copy.deepcopy(module)
        preserved=[p for p in original['lights'] if not R['is_added'](p)]
        if len(preserved)!=23:raise RuntimeError('Reception original lamp set changed; preserve it')
        rows=R['apply_module'](module)
        if [p for p in module['lights'] if not R['is_added'](p)]!=preserved:raise RuntimeError('Existing lights changed')
        if [p for p in module['parts'] if not R['is_added'](p)]!=[p for p in original['parts'] if not R['is_added'](p)]:raise RuntimeError('Existing geometry changed')
        if module.get('postprocess_lighting')!=original.get('postprocess_lighting') or module.get('runtime_actors')!=original.get('runtime_actors'):raise RuntimeError('Exposure or runtime actors changed')
        if [m for m in catalog['modules'] if m['id']!=R['MODULE']]!=[m for m in before['modules'] if m['id']!=R['MODULE']]:raise RuntimeError('Other modules changed')
        bank['contract_sha1']=contract(catalog)
        # Preserve all existing hard dependencies and append the reused kit only.
        assets=list(generator.get_editor_property('module_assets'));known={a.get_path_name() for a in assets if a}
        for path in [R['MESH'],*R['MATERIALS']]:
            a=u.load_asset(path)
            if not a:raise RuntimeError('Missing fixture asset '+path)
            if a.get_path_name() not in known:assets.append(a);known.add(a.get_path_name())
        generator.modify();generator.set_editor_property('module_assets',assets)
        generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
        save(world,TARGET)
        (FLOW/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
        (FLOW/'Config/layout-bank-v1.json').write_text(json.dumps(bank,ensure_ascii=False,separators=(',',':')),encoding='utf8')
        report.update(stage='production_saved',original_light_count=len(preserved),original_light_sha256=digest(preserved),
            original_lights_preserved=True,existing_parts_preserved=True,postprocess_preserved=True,other_modules_preserved=True,
            layout_entries_preserved=bank['entries']==before['facility_flow']['layout_bank']['entries'],
            added_lights=len(rows),added_fixtures=len(rows),bank_contract_sha1=bank['contract_sha1'])
        report['maps'].append(dict(path=TARGET,saved=True));record()
        for target in R['SUBJECTS']:
            world=u.EditorLoadingAndSavingUtils.load_map(target)
            previous_lights=old_lights(world)
            if len(previous_lights)!=23:raise RuntimeError('Subject original lamp set changed: '+target)
            changes=R['apply_subject'](world)
            if old_lights(world)!=previous_lights:raise RuntimeError('Original subject lighting changed: '+target)
            if any(row['forward'][2]>-.9999 for row in changes):raise RuntimeError('Supplemental fixture points upward')
            save(world,target)
            report['maps'].append(dict(path=target,saved=True,original_lights_preserved=True,changes=changes));record()
        report['stage']='maps_saved';record()
        print('RECEPTION_GROUND_LIGHTING_SAVED',len(report['maps']),'maps;',len(preserved),'existing lamps preserved;',len(rows),'additional fixtures')
    except Exception:
        report['error']=traceback.format_exc();record();raise
    finally:
        if previous and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
            u.EditorLoadingAndSavingUtils.load_map(previous)

if __name__=='__main__':main()
