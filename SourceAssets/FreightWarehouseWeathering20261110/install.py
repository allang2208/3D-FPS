"""Apply the weathering sample only to the user's existing freight/station subject."""
from pathlib import Path
from datetime import datetime
import json,shutil,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
PLAN=json.loads((ROOT/'Config/layout.json').read_text('utf8'))
INPUTS=json.loads((ROOT/'inputs.json').read_text('utf8'))
TARGET=PLAN['map'];BASELINE=PLAN['baseline_map'];TAG=PLAN['tag']
RECEIPT=ROOT/'Receipts/install.json'

def vec(v):return list(v.to_tuple())
def close(a,b):return all(abs(x-y)<.01 for x,y in zip(a,b))

def save_world(world,target):
    suffix=target.removeprefix('/Game/').lower()
    prefixes=('/game/__externalactors__/'+suffix+'/', '/game/__externalobjects__/'+suffix+'/')
    dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    owned=[p for p in dirty if p.get_name()==target or p.get_name().lower().startswith(prefixes)]
    if owned and not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Could not save subject actor packages')
    if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Could not save subject '+target)
    return [p.get_name() for p in owned]

def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('Preserve active gameplay')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    prefix='/game/__externalactors__/gamemaps/design/l_freighttransit_theme_subject/'
    if any(p.get_name().lower().startswith(prefix) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved subject actors')
    assets=json.loads((ROOT/'Receipts/assets.json').read_text('utf8'))
    if assets.get('stage')!='assets_saved':raise RuntimeError('Weathering materials must be saved first')
    materials=assets['materials']
    previous=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else ''
    prior=json.loads(RECEIPT.read_text('utf8')) if RECEIPT.exists() else {}
    if prior.get('stage')=='map_saved':
        print('FREIGHT_WEATHERING_ALREADY_SAVED '+TARGET,flush=True);return
    if u.EditorAssetLibrary.does_asset_exist(BASELINE) and prior.get('baseline_map')!=BASELINE:raise RuntimeError('Preserve pre-existing comparison map')
    backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True)
    relative=TARGET.removeprefix('/Game/')
    for path in [PROJECT/'Content'/(relative+'.umap')]+[PROJECT/'Content'/folder/relative for folder in ('__ExternalActors__','__ExternalObjects__')]:
        if not path.exists():continue
        dest=backup/path.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True)
        if path.is_dir():shutil.copytree(path,dest)
        else:shutil.copy2(path,dest)
    report=dict(stage='preparing',map=TARGET,baseline_map=BASELINE,backup=str(backup),
        tests_run=False,game_run=False,rendered=False,editor_opened=False,production_map_modified=False)
    def record():RECEIPT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    record()
    try:
        world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
        if not world:raise RuntimeError('Requested freight subject unavailable')
        actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
        current={a.get_name():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
        # Preserve edits made after the authoring snapshot. Only the warehouse
        # and its container access areas are relevant to this art installation.
        for row in INPUTS['actors']:
            p=row['position']
            relevant='AbandonedCargoWarehouse' in row['tags'] or (2260<p[0]<5260 and -2300<p[1]<500 and row['class_name']=='ColdSteelSceneContainer')
            if not relevant:continue
            actor=current.get(row['name'])
            if actor is None or not close(vec(actor.get_actor_location()),p) or not close(vec(actor.get_actor_rotation()),row['rotation']) or not close(vec(actor.get_actor_scale3d()),row['scale']):
                raise RuntimeError('Preserve changed warehouse placement '+row['name'])
        for binding in PLAN['bindings']:
            actor=current[binding['actor']]
            component=next(c for c in actor.get_components_by_class(u.StaticMeshComponent) if c.get_name()==binding['component'])
            if component.static_mesh.get_path_name()!=binding['mesh'] or component.get_material(binding['slot']).get_path_name()!=binding['before']:
                raise RuntimeError('Preserve changed subject surface '+binding['actor'])
        if not u.EditorAssetLibrary.does_asset_exist(BASELINE):
            if not u.EditorLoadingAndSavingUtils.save_map(world,BASELINE):raise RuntimeError('Comparison map save failed')
            report['stage']='baseline_saved';record()
            world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
            current={a.get_name():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
        for binding in PLAN['bindings']:
            actor=current[binding['actor']];actor.modify()
            component=next(c for c in actor.get_components_by_class(u.StaticMeshComponent) if c.get_name()==binding['component'])
            component.modify();component.set_material(binding['slot'],u.load_asset(materials[binding['after']]))
        # A retry before any successful map save can only leave owned transient
        # actors in a live editor. Restrict replacement to this revision's tag.
        for actor in list(current.values()):
            if TAG in [str(v) for v in actor.tags]:actors.destroy_actor(actor)
        cache={}
        def asset(path):
            if path not in cache:cache[path]=u.load_asset(path)
            if not cache[path]:raise RuntimeError('Dressing asset missing '+path)
            return cache[path]
        def named(actor,row):
            actor.set_actor_label('WarehouseWeathering_'+row['id'])
            actor.set_folder_path('StationLine/WarehouseWeathering/'+row['group'])
            actor.set_editor_property('tags',[u.Name(TAG),u.Name('AbandonedCargoWarehouse'),u.Name('StationLine.Subject')])
        for row in PLAN['parts']:
            actor=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*row['position']),u.Rotator(pitch=0,yaw=row['yaw'],roll=0))
            named(actor,row);component=actor.static_mesh_component
            component.set_static_mesh(asset(row['mesh']));actor.set_actor_scale3d(u.Vector(*row['scale']))
            component.set_collision_profile_name('NoCollision');component.set_mobility(u.ComponentMobility.STATIC)
            component.set_cast_shadow(row['cast_shadow']);component.set_editor_property('ld_max_draw_distance',row['max_draw_distance'])
        for row in PLAN['decals']:
            actor=actors.spawn_actor_from_class(u.DecalActor,u.Vector(*row['position']),u.Rotator(pitch=row['pitch'],yaw=row['yaw'],roll=row['roll']))
            named(actor,row);component=actor.get_component_by_class(u.DecalComponent)
            actor.set_actor_location(u.Vector(*row['position']),False,True)
            actor.set_actor_rotation(u.Rotator(pitch=row['pitch'],yaw=row['yaw'],roll=row['roll']),True)
            component.set_decal_material(asset(materials[row['material']]))
            component.set_editor_property('decal_size',u.Vector(*row['size']))
            component.set_editor_property('sort_order',3 if row['material']=='Rust' else 2)
            component.set_editor_property('fade_screen_size',.002)
        report.update(stage='map_saved',saved_packages=save_world(world,TARGET),
            material_bindings=PLAN['bindings'],decorative_meshes=len(PLAN['parts']),decals=len(PLAN['decals']),groups=PLAN['groups'],
            preserved=['room geometry','existing actors and transforms','container IDs and opening logic','route','player start','lights','production dungeon'],
            entry_command='open '+TARGET,comparison_command='open '+BASELINE,return_command='open /Game/GameMaps/DayNight_Lighting')
        record();print('FREIGHT_WAREHOUSE_WEATHERING_MAP_SAVED '+TARGET,flush=True)
        if previous and not previous.startswith('/Temp/') and previous not in (TARGET,BASELINE):u.EditorLoadingAndSavingUtils.load_map(previous)
    except Exception:
        report['error']=traceback.format_exc();record();raise

if __name__=='__main__':main()
