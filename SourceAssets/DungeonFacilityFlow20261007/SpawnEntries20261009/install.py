"""Import closed static fixtures and withdraw all emergence wiring from the production map."""
from pathlib import Path
from datetime import datetime
import unreal as u
import json,runpy,importlib.util,shutil,traceback,hashlib,gzip,math
ROOT=Path(__file__).resolve().parent;FLOW=ROOT.parent;PROJECT=FLOW.parents[1]
TARGET='/Game/GameMaps/L_Dungeon_Randomized';BASE='/Game/Dungeons/SpawnEntries20261009'
E=u.EditorAssetLibrary
report=dict(stage='preparing',game_run=False,editor_opened=False,saved_assets=[],checks=[])
def record():(ROOT/'latest-attempt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def save(asset):
    asset.modify()
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
    report['saved_assets'].append(asset.get_path_name())

def main():
    record();editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('Preserve active PIE; no writes')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
    files=[PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap']
    for category in ('__ExternalActors__','__ExternalObjects__'):
        folder=PROJECT/'Content'/category/'GameMaps/L_Dungeon_Randomized'
        if folder.exists():files.extend(p for p in folder.rglob('*') if p.is_file())
    for src in files:
        dest=backup/src.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
    report['backup']=str(backup);record()
    world=u.EditorLoadingAndSavingUtils.load_map(TARGET);gen=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)[0]
    before=gen.get_editor_property('module_catalog_json');catalog=json.loads(before)
    (backup/'catalog-before.json').write_text(before,encoding='utf8')
    # Rebuild cuts from original assets after moving an outlet; close obsolete
    # holes by restoring their original part before applying this revision.
    previous=ROOT/'floor-assets.json'
    if previous.exists():
        by_id={m['id']:m for m in catalog['modules']}
        for mid,changes in json.loads(previous.read_text('utf8')).items():
            for c in changes:
                part=by_id[mid]['parts'][c['part_index']]
                if part['mesh'].split('.')[0]==c['mesh']:part['mesh']=c['source']
    spec=importlib.util.spec_from_file_location('spawn_entry_import',PROJECT/'SourceAssets/DungeonReceptionHall20261006/install.py')
    imp=importlib.util.module_from_spec(spec);spec.loader.exec_module(imp)
    imp.ROOT=ROOT;imp.BASE=BASE;imp.OWNER='SpawnEntries20261009';imp.MAP='/Game/GameMaps/Design/Unused_SpawnEntryImport';imp.report=dict(saved_assets=[]);imp.record=lambda:None
    imp.MAN=json.loads((ROOT/'geometry.json').read_text('utf8'));imp.meshes();report['saved_assets']+=imp.report['saved_assets'];record()
    # Only closed door geometry blocks movement. The floor under every lid is
    # restored by the recipe, so no custom collision/support Actor is required.
    for item in imp.MAN['meshes']:
        if item['kind'] in ('DoorBody','DoorLeaf','DoorLeafRight'):
            mesh=u.load_asset(item['mesh'])
            mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            save(mesh)
    contract=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash']
    updated=runpy.run_path(str(ROOT/'recipe.py'))['extend'](catalog,contract)
    deps={a.get_path_name():a for a in gen.get_editor_property('module_assets') if a and not a.get_path_name().startswith(BASE+'/')}
    for path in report['saved_assets']:
        a=u.load_asset(path);deps[a.get_path_name()]=a
    gen.modify();gen.set_editor_property('module_catalog_json',json.dumps(updated,ensure_ascii=False));gen.set_editor_property('module_assets',list(deps.values()))
    refs=gen.get_editor_property('module_asset_paths')
    gen.set_editor_property('module_asset_paths',[r for r in refs if BASE+'/' not in (r.get_path_name() if isinstance(r,u.Object) else str(r))])
    # An editor-generated preview may still contain the retired native Actor.
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        if actor.get_class().get_path_name()=='/Script/FPSGAME.DungeonSpawnEntry':
            u.get_editor_subsystem(u.EditorActorSubsystem).destroy_actor(actor)
    dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    owned=[p for p in dirty if p.get_name()==TARGET or any(p.get_name().lower().startswith('/game/'+folder+'/gamemaps/l_dungeon_randomized/') for folder in ('__externalactors__','__externalobjects__'))]
    if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Could not save generator package')
    if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Could not save map')
    (FLOW/'Config/catalog.json').write_text(json.dumps(updated,ensure_ascii=False,indent=2),encoding='utf8')
    (FLOW/'Config/layout-bank-v1.json').write_text(json.dumps(updated['facility_flow']['layout_bank'],ensure_ascii=False,separators=(',',':')),encoding='utf8')
    placements=json.loads((ROOT/'placements.json').read_text('utf8'))
    report.update(stage='map_saved',mode='closed_static_fixtures',emergence_runtime_removed=True,rooms=sum(bool(v) for v in placements.values()),entries=sum(len(v) for v in placements.values()),map=TARGET,bank_contract_sha1=contract(updated))
    record();(ROOT/'install-receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');u.log('DUNGEON_CLOSED_FIXTURES_SAVED')
try:main()
except Exception:report['error']=traceback.format_exc();record();raise
