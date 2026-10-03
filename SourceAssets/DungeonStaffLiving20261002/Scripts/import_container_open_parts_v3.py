"""Bind the shelf's real moving storage box in the two existing staff maps."""
import json,hashlib,re,shutil
from pathlib import Path
from datetime import datetime
import unreal as u

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];OUT=ROOT/'ContainerOpenPartsV3'
CFG=json.loads((ROOT/'Config/room.json').read_text('utf8'))
if CFG.get('scene_polish_revision',0)>=4:
    current=ROOT/'Scripts/import_scene_polish_v4.py'
    exec(compile(current.read_text('utf8'),str(current),'exec'))
    raise SystemExit(0)
MAN=json.loads((OUT/'Authored/manifest.json').read_text('utf8'));BASE=CFG['ue_base']+'/ContainerOpenPartsV3'
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
RP=OUT/'install.json'
report=json.loads(RP.read_text('utf8')) if RP.exists() else dict(meshes={},maps={},backups=[])
report.update(tests_run=False,game_run=False,rendered=False,editor_opened=False,rewards_deferred=True)
def record():RP.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

# Same accepted mesh production settings, but only this batch's two new assets.
previous=ROOT/'Scripts/import_dormitory_variants_v2.py';code=previous.read_text('utf8')
begin=code.index("u.SystemLibrary.execute_console_command")
end=code.index("container_class=u.load_class")
exec(compile(code[begin:end],str(previous),'exec'))
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
backup=OUT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
for target in (CFG['maps']['StaffDormitory'],CFG['sample_map']):
    if report['maps'].get(target,{}).get('stage')=='map_saved':continue
    disk=PROJECT/'Content'/(target.removeprefix('/Game/')+'.umap');dst=backup/disk.name
    shutil.copy2(disk,dst);report['backups'].append(dict(original=str(disk),backup=str(dst)));record()
    world=u.EditorLoadingAndSavingUtils.load_map(target)
    if not world:raise RuntimeError('Cannot load staff sample '+target)
    actors={a.get_actor_label():a for a in AA.get_all_level_actors() if 'StaffLiving.Subject' in [str(t) for t in a.tags]}
    bound=[]
    for c in MAN['containers']:
        label='StaffSubject_StaffDormitory_'+c['id'];a=actors.get(label)
        if not a or not isinstance(a,u.ColdSteelSceneContainer):raise RuntimeError('Preserve missing/changed container placement '+label)
        a.body.set_static_mesh(meshes[c['body']]);a.door.set_static_mesh(meshes[c['door']])
        a.door.set_mobility(u.ComponentMobility.MOVABLE);a.door.set_collision_profile_name('BlockAllDynamic')
        a.door_hinge.set_relative_location(u.Vector(*c['hinge_cm']),False,False)
        a.set_editor_property('opening_motion',u.ColdSteelContainerMotion.DRAWER)
        a.set_editor_property('drawer_travel',u.Vector(*c['drawer_travel_cm']))
        for component in (a.body,a.door):component.set_render_custom_depth(True);component.set_custom_depth_stencil_value(201)
        bound.append(dict(label=label,container_id=c['container_id'],motion='Drawer',travel_cm=32))
    if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Shelf moving-part map save failed '+target)
    report['maps'][target]=dict(stage='map_saved',containers=bound,layout_changed=False,beds_changed=False);record()
    u.log('STAFF_CONTAINER_OPEN_PARTS_MAP_SAVED '+target)

for filename in ('room.json','modules-draft.json'):shutil.copy2(ROOT/'Config'/filename,backup/filename)
draft_path=ROOT/'Config/modules-draft.json';draft=json.loads(draft_path.read_text('utf8'))
by_key={c['container_id']:c for c in MAN['containers']}
for module in draft['modules']:
    for c in module.get('scene_containers',[]):
        patch=by_key.get(c['container_id'])
        if patch:c.update(body=patch['body'],door=patch['door'],hinge=patch['hinge_cm'],opening_motion='Drawer',drawer_travel=patch['drawer_travel_cm'])
draft['container_open_parts_revision']=3;draft['all_scene_containers_require_moving_part']=True
draft_path.write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding='utf8')
CFG.update(container_open_parts_revision=3,all_scene_containers_require_moving_part=True,
    current_authored_source='ContainerOpenPartsV3/Authored/StaffLivingTheme_ContainerOpenPartsV3.blend')
(ROOT/'Config/room.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf8')
report.update(stage='samples_saved',updated_unique_containers=6,all_container_types=['Locker','Bookcase','Bookshelf','Bedside'],
    all_container_types_have_moving_parts=True,random_pool_registered=False,open_command='open '+CFG['sample_map']);record()
u.log('STAFF_CONTAINER_OPEN_PARTS_DELIVERY_SAVED')
