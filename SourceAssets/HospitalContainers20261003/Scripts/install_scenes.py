"""Merge only hospital container additions into the latest saved production and sample maps."""
import hashlib
import json
import runpy
import shutil
import traceback
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
PRODUCTION='/Game/GameMaps/L_Dungeon_Randomized'
PREVIEW='/Game/GameMaps/Design/L_Hospital_Theme_Subject'
LINE=PROJECT/'SourceAssets/DungeonHospitalLine20261003'
read=lambda p:json.loads(p.read_text('utf-8-sig'))
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
existing_editor=globals().get('HOSPITAL_CONTAINERS_EXISTING_EDITOR',False)
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and not existing_editor:
    raise RuntimeError('Background commandlet or existing editor bridge required')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active game session')
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
if dirty:raise RuntimeError('Preserve unsaved maps: '+str(dirty))
build=read(ROOT/'Receipts/native-build.json')
if build.get('stage')!='binaries_saved':raise RuntimeError('Bedside native implementation must be built before map save')
imported=read(ROOT/'Receipts/assets.json')
if imported.get('stage')!='assets_saved':raise RuntimeError('Hospital assets must be saved first')
rules_helpers=runpy.run_path(str(ROOT/'Scripts/catalog_rules.py'))
ue_helpers=runpy.run_path(str(ROOT/'Scripts/unreal_helpers.py'))
rules=rules_helpers['rules']();actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
original=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else ''
report=dict(stage='saving',maps={},tests_run=False,rendered=False,game_run=False,editor_opened=False,
    rewards_deferred=True,bedside_count_is_requested=True)
receipt=ROOT/'Receipts/install.json'
(ROOT/'Backup').mkdir(exist_ok=True)

def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
def record():write(receipt,report)
def backup(path):
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    destination=ROOT/'Backup'/(path.stem+'-'+digest[:12]+path.suffix)
    if not destination.exists():shutil.copy2(path,destination)
    return digest
def map_backup(target):return backup(PROJECT/'Content'/(target.removeprefix('/Game/')+'.umap'))
def asset(path):
    value=u.load_asset(path)
    if not value:raise RuntimeError('Required hospital asset unavailable '+path)
    return value

try:
    record();old=map_backup(PRODUCTION)
    world=u.EditorLoadingAndSavingUtils.load_map(PRODUCTION)
    if not world:raise RuntimeError('Saved production dungeon unavailable')
    generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
    if len(generators)!=1:raise RuntimeError('Production generator unavailable')
    generator=generators[0];before=generator.get_editor_property('module_catalog_json')
    (ROOT/'Backup'/('catalog-'+hashlib.sha256(before.encode()).hexdigest()[:12]+'.json')).write_text(before,encoding='utf8')
    catalog=rules_helpers['extend'](json.loads(before))
    hard={a.get_path_name():a for a in generator.get_editor_property('module_assets') if a}
    dependencies=list(rules_helpers['paths'](rules))+imported['materials']+imported['textures']
    for module in catalog['modules']:
        if module['id'] in rules['groups']:dependencies.extend(module.get('runtime_assets',[]))
    for path in sorted(set(dependencies)):
        obj=asset(path);hard[obj.get_path_name()]=obj
    generator.modify();generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
    generator.set_editor_property('module_assets',list(hard.values()))
    ue_helpers['ensure_outline'](actors,rules['outline'],'Dungeon_SceneContainerOutline',asset)
    if not u.EditorLoadingAndSavingUtils.save_map(world,PRODUCTION):raise RuntimeError('Production map save failed')
    report['maps'][PRODUCTION]=dict(stage='map_saved',previous_sha256=old,modules=list(rules['groups']),
        count_ranges=rules['count_ranges'],bedside_spawn='native occupancy-based after upright beds')
    record()

    old=map_backup(PREVIEW);world=u.EditorLoadingAndSavingUtils.load_map(PREVIEW)
    if not world:raise RuntimeError('Saved hospital sample unavailable')
    line=read(LINE/'Config/line.json');modules={m['id']:m for m in catalog['modules']}
    polish=PROJECT/'SourceAssets/HospitalPolish20261003'
    polish_receipt=polish/'Receipts/assets.json'
    fixture_counts={}
    if polish_receipt.exists() and read(polish_receipt).get('stage')=='assets_saved':
        fixture_counts=runpy.run_path(str(polish/'Scripts/integration_helpers.py'))['update_preview'](actors,line,asset)
    office=PROJECT/'SourceAssets/HospitalDoctorOffice20261003'
    office_receipt=office/'Receipts/assets.json'
    if office_receipt.exists() and read(office_receipt).get('stage')=='assets_saved':
        fixture_counts.update(runpy.run_path(str(office/'Scripts/integration_helpers.py'))['update_preview'](actors,line,asset))
    for actor in actors.get_all_level_actors():
        if ue_helpers['OWNED_TAG'] in [str(t) for t in actor.tags]:actors.destroy_actor(actor)
    selected={}
    for offset,(identity,groups) in enumerate(rules['groups'].items()):
        pose=next(p for p in line['placements'] if p['id']==identity)
        groups=[g for g in modules[identity]['warehouse_containers']['groups'] if g['id'].startswith('Hospital.')]
        containers=rules_helpers['choose'](groups,rules['preview_seed']+offset);selected[identity]=[]
        for spec in containers:
            ue_helpers['spawn_container'](actors,spec,pose,asset)
            selected[identity].append(dict(id=spec['container_id'],position=spec['position'],yaw=spec['yaw']))
    module=modules['AbandonedIsolationWard'];bed_specs=[s for s in module['runtime_actors'] if s['type']=='beds']
    scatter=[actor for actor in actors.get_all_level_actors() if isinstance(actor,u.WardBedScatter)
        and 'AbandonedIsolationWard' in [str(t) for t in actor.tags]]
    if len(scatter)!=len(bed_specs):raise RuntimeError('Preserve changed hospital bed scatter layout before adapting it')
    for actor,spec in zip(scatter,bed_specs):
        actor.modify();ue_helpers['configure_bedside'](actor,spec,asset)
        actor.set_editor_property('room_props',[ue_helpers['struct'](u.WardRoomProp,
            type_id=u.Name(p['id']),mesh=asset(p['mesh']),min_per_room=p['min_per_room'],max_per_room=p['max_per_room'],
            clearance=p['clearance'],blocking=p['blocking']) for p in spec['room_props']])
        actor.set_editor_property('keep_clear',[u.Box(min=u.Vector(*b['min']),max=u.Vector(*b['max'])) for b in spec['keep_clear']])
    ue_helpers['ensure_outline'](actors,rules['outline'],'HospitalLine_ContainerOutline',asset,True)
    if not u.EditorLoadingAndSavingUtils.save_map(world,PREVIEW):raise RuntimeError('Hospital sample save failed')
    report['maps'][PREVIEW]=dict(stage='map_saved',previous_sha256=old,preview_seed=rules['preview_seed'],
        authored_container_count=sum(map(len,selected.values())),selected=selected,
        bedside_count_requested=[rules['bedside']['min_count'],rules['bedside']['max_count']],
        bedside_policy='wall bays in rooms with upright beds, reserve lid sweep, omit blocked placements')
    report['maps'][PREVIEW]['fixtures']=fixture_counts
    record()

    # Preserve unrelated module data in each local authoring mirror.
    catalog_files=('DungeonRoutes20260922/Config/catalog.json','DungeonThemedRoutes20261001/Config/catalog.json',
        'WarehouseContainers20261002/Config/catalog.json','DungeonSplitLevels20261001/Config/catalog.json',
        'DungeonStaffLiving20261002/Production20261002/Config/catalog.json','StationWorkshop20261003/Config/catalog.json',
        'SceneLootExpansion20261003/Config/catalog.json','DungeonHospitalLine20261003/Config/production-catalog-snapshot.json')
    report['mirrors_saved']=[]
    for relative in catalog_files:
        path=PROJECT/'SourceAssets'/relative
        if path.exists():
            backup(path);write(path,rules_helpers['extend'](read(path)));report['mirrors_saved'].append(relative)
    # Individual room rebuild inputs keep their architecture and other gameplay descriptors.
    for relative in ('DungeonIsolationWard20260929/Config/module.json',
                     'DungeonAnatomyTheatre20261001/Pool20261001/Config/module.json'):
        path=PROJECT/'SourceAssets'/relative
        if path.exists():backup(path);write(path,rules_helpers['extend_module'](read(path)))
    write(ROOT/'Config/catalog.json',catalog)
    line.update(hospital_container_revision=rules['revision'],hospital_container_count_ranges=rules['count_ranges'],
        hospital_authored_container_count=sum(map(len,selected.values())),hospital_bedside_requested=[2,3],
        hospital_container_preview_seed=rules['preview_seed'],container_rewards_deferred=True,
        source_catalog_sha256=hashlib.sha256(json.dumps(catalog,ensure_ascii=False).encode()).hexdigest())
    if fixture_counts:line.update(hospital_fixture_revision=2,hospital_fixture_author='SourceAssets/HospitalPolish20261003')
    write(LINE/'Config/line.json',line)
    report.update(stage='maps_saved',original_map=original);record()
    print('HOSPITAL_CONTAINER_MAPS_SAVED '+str(sum(map(len,selected.values())))+' AUTHORED + 2-3 REQUESTED BEDSIDE',flush=True)
except Exception:
    report.update(stage='save_failed',error=traceback.format_exc());record();raise
finally:
    if existing_editor and original and u.EditorAssetLibrary.does_asset_exist(original):u.EditorLoadingAndSavingUtils.load_map(original)
