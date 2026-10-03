"""Save accepted staff modules and references into the existing production generator."""
import json,hashlib,runpy,shutil
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];STAFF=ROOT.parent;PROJECT=STAFF.parents[1]
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():raise RuntimeError('Background commandlet required')
build=json.loads((ROOT/'Receipts/native-build.json').read_text('utf-8-sig'))
if build.get('editor_exit')!=0 or build.get('game_exit')!=0:raise RuntimeError('Preserve current production map until the new native assembly is built')
backup=ROOT/'Backup';backup.mkdir(parents=True,exist_ok=True)
disk=PROJECT/'Content/GameMaps/L_Dungeon_Randomized.umap';digest=hashlib.sha256(disk.read_bytes()).hexdigest()
dest=backup/('L_Dungeon_Randomized-'+digest[:12]+'.umap')
if not dest.exists():shutil.copy2(disk,dest)
world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
if not world:raise RuntimeError('Production map unavailable')
gs=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(gs)!=1:raise RuntimeError('Production generator unavailable')
g=gs[0];before=g.get_editor_property('module_catalog_json')
(backup/('catalog-'+hashlib.sha256(before.encode()).hexdigest()[:12]+'.json')).write_text(before,encoding='utf8')
helper=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))
catalog=helper['extend'](json.loads(before))
assets={a.get_path_name():a for a in g.get_editor_property('module_assets') if a}
staffdata=json.loads((ROOT/'Config/modules.json').read_text('utf8'))
for path in sorted(set(helper['asset_paths'](staffdata))):
    a=u.load_class(None,path) if path.startswith('/Script/') or path.endswith('_C') else u.load_asset(path)
    if not a:raise RuntimeError('Missing production dependency '+path)
    assets[a.get_path_name()]=a
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
g.set_editor_property('module_assets',list(assets.values()))
label='Dungeon_SceneContainerOutline'
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
pp=next((a for a in AA.get_all_level_actors() if a.get_actor_label()==label),None)
if not pp:pp=AA.spawn_actor_from_class(u.PostProcessVolume,u.Vector())
pp.set_actor_label(label);pp.set_folder_path('DungeonRoutes/Environment');pp.set_editor_property('unbound',True)
pp.set_editor_property('priority',1.);pp.set_editor_property('tags',[u.Name('ColdSteel.SceneContainer.Outline')])
settings=pp.get_editor_property('settings');blend=u.WeightedBlendable()
blend.set_editor_property('weight',1.);blend.set_editor_property('object',u.load_asset(staffdata['container_outline']))
blends=u.WeightedBlendables();blends.set_editor_property('array',[blend]);settings.set_editor_property('weighted_blendables',blends)
pp.set_editor_property('settings',settings)
if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Production map save failed')
text=json.dumps(catalog,ensure_ascii=False,indent=2)
for p in (ROOT/'Config/catalog.json',PROJECT/'SourceAssets/DungeonRoutes20260922/Config/catalog.json',
          PROJECT/'SourceAssets/DungeonThemedRoutes20261001/Config/catalog.json',
          PROJECT/'SourceAssets/DungeonSplitLevels20261001/Config/catalog.json'):
    p.write_text(text,encoding='utf8')
cp=STAFF/'Config/room.json';cfg=json.loads(cp.read_text('utf8'));shutil.copy2(cp,backup/'room-before-production.json')
cfg.update(phase='production',random_pool_registered=True,production_revision=1,production_map=TARGET,
    production_modules='Production20261002/Config/modules.json',accepted_by_user=True,
    theme_candidates=4,branches_per_run=3,container_rewards_deferred=True,
    gameplay_scope='Production themed combat rooms, seeded furniture layouts and searchable scene containers; reward table deferred.')
cp.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
report=dict(stage='map_saved',map=TARGET,sequence=staffdata['sequence'],theme_candidates=4,branches_per_run=3,
    unique_scene_containers=sum(len(m['scene_containers']) for m in staffdata['modules']),hard_dependencies=len(assets),
    previous_map_sha256=digest,tests_run=False,rendered=False,generation_executed=False,editor_opened=False,
    rewards_deferred=True,samples_retirement='pending',save_mode='background_commandlet')
(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('STAFF_LIVING_PRODUCTION_MAP_SAVED',flush=True)
