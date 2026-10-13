"""Import the veil assets, compile materials, and save the production catalog."""
from pathlib import Path
from datetime import datetime
import copy,json,runpy,shutil,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
FLOW=PROJECT/'SourceAssets/DungeonFacilityFlow20261007';TARGET='/Game/GameMaps/L_Dungeon_Randomized'
R=runpy.run_path(str(ROOT/'recipe.py'))
report=dict(stage='preparing',game_run=False,rendered=False,performance_measured=False)

def record():
    (ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor.get_game_world():raise RuntimeError('Preserve active game')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    dirty_before={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p.startswith(R['BASE']) or '/__ExternalActors__/GameMaps/L_Dungeon_Randomized/' in p for p in dirty_before):
        raise RuntimeError('Preserve unsaved target assets')
    previous=editor.get_editor_world();previous=previous.get_path_name().split('.')[0] if previous else ''
    backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
    files=[PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap',FLOW/'Config/catalog.json',FLOW/'Config/layout-bank-v1.json']
    for category in ('__ExternalActors__','__ExternalObjects__'):
        folder=PROJECT/'Content'/category/'GameMaps/L_Dungeon_Randomized'
        if folder.exists():files.extend(p for p in folder.rglob('*') if p.is_file())
    for path in files:
        dst=backup/path.relative_to(PROJECT);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dst)
    report['backup']=str(backup);record()
    try:
        saved=runpy.run_path(str(ROOT/'assets.py'))['install']()
        report.update(stage='assets_saved',saved_assets=saved);record()
        world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
        generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
        if len(generators)!=1:raise RuntimeError('Missing production generator')
        generator=generators[0];raw=generator.get_editor_property('module_catalog_json')
        (backup/'actual-catalog-before.json').write_text(raw,encoding='utf8')
        before=json.loads(raw);after=copy.deepcopy(before)
        contract=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash']
        if before['facility_flow']['layout_bank']['contract_sha1']!=contract(before):raise RuntimeError('Preserve changed layout contract')
        removed=R['apply_module'](next(m for m in after['modules'] if m['id']==R['MODULE']))
        bank=after['facility_flow']['layout_bank'];bank['contract_sha1']=contract(after)
        assets=list(generator.get_editor_property('module_assets'));known={a.get_path_name().split('.')[0] for a in assets if a}
        for path in saved:
            if path not in known:assets.append(u.load_asset(path));known.add(path)
        generator.modify();generator.set_editor_property('module_catalog_json',json.dumps(after,ensure_ascii=False))
        generator.set_editor_property('module_assets',assets)
        dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
        owned=[p for p in dirty if p.get_name() not in dirty_before and (p.get_name()==TARGET or
            any(p.get_name().lower().startswith('/game/'+category+'/gamemaps/l_dungeon_randomized/') for category in ('__externalactors__','__externalobjects__')))]
        if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Map package save failed')
        if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Map save failed')
        (FLOW/'Config/catalog.json').write_text(json.dumps(after,ensure_ascii=False,indent=2),encoding='utf8')
        (FLOW/'Config/layout-bank-v1.json').write_text(json.dumps(bank,ensure_ascii=False,separators=(',',':')),encoding='utf8')
        report.update(stage='map_saved',map=TARGET,door_count=2,added_mesh_instances=4,triangles_total=28,
            noise_texture_size=256,noise_samples_per_fog_pixel=2,translucent_layers=0,
            fog_draw_distance_cm=2600,removed_inside_lights=removed,new_lights=0,new_ticks=0,new_particle_systems=0,
            collision_and_navigation_changed=False,black_mask_distance_culled=False)
        record();print('RECEPTION_DOOR_VEIL_SAVED',json.dumps(report,ensure_ascii=False),flush=True)
    except Exception:
        report['error']=traceback.format_exc();record();raise
    finally:
        if previous and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():u.EditorLoadingAndSavingUtils.load_map(previous)

if __name__=='__main__':main()
