"""Save only the office ceiling light's no-shadow policy and corresponding actor."""
import hashlib,json,shutil
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent;PROJECT=ROOT.parents[2]
LIGHT_ID='StationWorkshop.MaintenanceCeiling';LABEL='StationWorkshop_Light_0'
for name in ('Receipts','Backup'):(ROOT/name).mkdir(parents=True,exist_ok=True)
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and not globals().get('STATION_LIGHT_EXISTING_EDITOR',False):raise RuntimeError('Commandlet or existing editor bridge required')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active game session before light save')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()}
if dirty:raise RuntimeError('Preserve unsaved maps before light save: '+str(sorted(dirty)))
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
original=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else ''
report=dict(stage='saving',maps={},light_id=LIGHT_ID,cast_shadows=False,tests_run=False,rendered=False,game_run=False,editor_opened=False)
receipt=ROOT/'Receipts/install.json'
def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
def record():write(receipt,report)
def no_shadow(value):
    if isinstance(value,list):return [no_shadow(v) for v in value]
    if isinstance(value,dict):
        out={k:no_shadow(v) for k,v in value.items()}
        if out.get('id')==LIGHT_ID:out['cast_shadows']=False
        return out
    return value
def backup(target):
    path=PROJECT/'Content'/(target.removeprefix('/Game/')+'.umap');digest=hashlib.sha256(path.read_bytes()).hexdigest()
    dest=ROOT/'Backup'/(path.stem+'-'+digest[:12]+'.umap')
    if not dest.exists():shutil.copy2(path,dest)
    return digest

target='/Game/GameMaps/L_Dungeon_Randomized';old=backup(target)
world=u.EditorLoadingAndSavingUtils.load_map(target)
generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
if len(generators)!=1:raise RuntimeError('Production generator unavailable')
g=generators[0];before=g.get_editor_property('module_catalog_json')
(ROOT/'Backup'/('catalog-'+hashlib.sha256(before.encode()).hexdigest()[:12]+'.json')).write_text(before,encoding='utf8')
catalog=no_shadow(json.loads(before))
g.modify();g.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Production map save failed')
report['maps'][target]=dict(stage='map_saved',previous_sha256=old);record()

target='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject';old=backup(target)
world=u.EditorLoadingAndSavingUtils.load_map(target)
light=next((a for a in AA.get_all_level_actors() if a.get_actor_label()==LABEL),None)
if not light:raise RuntimeError('Office ceiling light unavailable')
c=light.get_component_by_class(u.PointLightComponent)
if not c:raise RuntimeError('Office point-light component unavailable')
light.modify();c.modify();c.set_editor_property('cast_shadows',False)
if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Station preview save failed')
report['maps'][target]=dict(stage='map_saved',previous_sha256=old,actor=LABEL);record()

text=json.dumps(catalog,ensure_ascii=False,indent=2)
for relative in ('DungeonRoutes20260922/Config/catalog.json','DungeonThemedRoutes20261001/Config/catalog.json',
    'WarehouseContainers20261002/Config/catalog.json','DungeonSplitLevels20261001/Config/catalog.json',
    'DungeonStaffLiving20261002/Production20261002/Config/catalog.json','StationWorkshop20261003/Config/catalog.json',
    'SceneLootExpansion20261003/Config/catalog.json'):
    (PROJECT/'SourceAssets'/relative).write_text(text,encoding='utf8')
station=next(m for m in catalog['modules'] if m['id']=='AbandonedTransitStation')
for path in (PARENT/'Config/workshop.json',PARENT/'RefineV3/Config/workshop.json',PARENT/'RefineV4/Config/workshop.json'):
    data=json.loads(path.read_text('utf-8-sig'));write(path,no_shadow(data))
write(PROJECT/'SourceAssets/DungeonTransitStation20260928/Config/module.json',station)
report['stage']='maps_saved';record()
if original and original!=target and u.EditorAssetLibrary.does_asset_exist(original):u.EditorLoadingAndSavingUtils.load_map(original)
print('STATION_OFFICE_LIGHT_NO_SHADOW_MAPS_SAVED',flush=True)
