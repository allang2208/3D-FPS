"""Merge ecology into the saved generator and persist every runtime dependency."""
from pathlib import Path
import json,runpy,shutil,hashlib,traceback
import unreal as u
ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT.parent;PROJECT=SOURCE.parents[1]
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
build=json.loads((ROOT/'Receipts/native-build.json').read_text('utf-8-sig'))
if build.get('editor_exit')!=0 or build.get('game_exit')!=0:raise RuntimeError('Native assembly build is pending')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active play session')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
previous=editor.get_editor_world() if editor else None
previous=previous.get_path_name().split('.')[0] if previous else None
rules=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))
data=json.loads((ROOT/'Config/modules.json').read_text('utf8'))
report=dict(stage='saving',revision=rules['REVISION'],map=TARGET,sequence=data['sequence'],
    tests_run=False,rendered=False,generated=False,editor_started=False,samples_retirement='pending')
def record():
    (ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def backup(path):
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    dest=ROOT/'Backup'/path.relative_to(PROJECT).parent/(path.stem+'-'+digest[:12]+path.suffix)
    dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():shutil.copy2(path,dest)
    return digest
try:
    record()
    world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
    generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
    if len(generators)!=1:raise RuntimeError('Production generator unavailable')
    generator=generators[0]
    before=generator.get_editor_property('module_catalog_json')
    catalog=rules['extend'](json.loads(before))
    assets={a.get_path_name():a for a in generator.get_editor_property('module_assets') if a}
    for path in sorted(set(rules['asset_paths'](data['modules']))):
        obj=u.load_class(None,path) if path.startswith('/Script/') or path.endswith('_C') else u.load_asset(path)
        if not obj:raise RuntimeError('Required ecology asset unavailable: '+path)
        assets[obj.get_path_name()]=obj
    cfg=json.loads((SOURCE/'Config/room.json').read_text('utf8'))
    registry=u.AssetRegistryHelpers.get_asset_registry()
    options=u.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True,
        include_searchable_names=False,include_soft_management_references=False,include_hard_management_references=False)
    retiring=[r['map'] for r in cfg['rooms']]+[cfg['sample_map']]
    refs={p:[str(r) for r in registry.get_referencers(p,options) if str(r) not in retiring] for p in retiring}
    report['subject_external_referencers']=refs
    if any(refs.values()):raise RuntimeError('Retained map users require preserving their targets: '+str(refs))
    report['previous_map_sha256']=backup(PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap')
    generator.modify();generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
    generator.set_editor_property('module_assets',list(assets.values()))
    if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Production map save failed')
    report.update(stage='map_saved',theme_candidates=len(catalog['themed_routes']['routes']),branches_per_run=3,
        hard_dependencies=len(assets),scene_containers=sum(sum(a['type']=='scene_container' for a in m['runtime_actors']) for m in data['modules']),
        treasure_chests=sum(len(m['props']) for m in data['modules']))
    record()
    # Each mirror receives the same ecology-only merge against its own current
    # contents; unrelated in-progress author changes are not replaced.
    mirrors=['DungeonRoutes20260922','DungeonThemedRoutes20261001','DungeonSplitLevels20261001']
    for name in mirrors:
        path=PROJECT/'SourceAssets'/name/'Config/catalog.json'
        backup(path);current=json.loads(path.read_text('utf8'))
        path.write_text(json.dumps(rules['extend'](current),ensure_ascii=False,indent=2),encoding='utf8')
    (ROOT/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
    path=SOURCE/'Config/room.json';backup(path)
    cfg.update(phase='production',random_pool_registered=True,accepted_by_user=True,production_map=TARGET,
        production_revision=rules['REVISION'],production_modules='Production20261005/Config/modules.json',
        subject_status='retirement_pending',theme_candidates=report['theme_candidates'],branches_per_run=3)
    path.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
    report['author_mirrors_saved']=mirrors;record()
    print('ECOLOGY_PRODUCTION_SAVED '+json.dumps({k:report[k] for k in ('stage','theme_candidates','scene_containers','treasure_chests')}))
except Exception:
    report['error']=traceback.format_exc();record();raise
finally:
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and previous:
        u.EditorLoadingAndSavingUtils.load_map(previous)
