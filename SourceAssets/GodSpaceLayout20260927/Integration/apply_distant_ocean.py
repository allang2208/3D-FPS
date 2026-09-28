"""Replace only the hub backdrop and cloud settings; preserve all gameplay/layout."""
import json,hashlib,shutil
from pathlib import Path
import unreal as u
ROOT=Path(__file__).parent;PROJECT=ROOT.parents[2]
MAP='/Game/GameMaps/DayNight_Lighting';DEST='/Game/Props/GodSpaceLayout20260927'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('End PIE before saving the ocean backdrop')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps before applying ocean')
world=editor.get_editor_world() if editor else None
if not world or world.get_path_name().split('.')[0]!=MAP:world=u.EditorLoadingAndSavingUtils.load_map(MAP)
if not world:raise RuntimeError('Cannot load main hub')
mesh=u.load_asset(DEST+'/Meshes/SM_GodSpaceDistantOcean');cloudmat=u.load_asset(DEST+'/Materials/MI_GodSpaceCloudSea')
if not mesh or not cloudmat:raise RuntimeError('Import ocean assets first')
api=u.get_editor_subsystem(u.EditorActorSubsystem)
actors=list(u.GameplayStatics.get_all_actors_of_class(world,u.Actor))
sky=next(a for a in actors if a.get_components_by_class(u.SkyAtmosphereComponent))
src=PROJECT/'Content/GameMaps/DayNight_Lighting.umap'
dst=PROJECT/'trash/godspace-ocean-continuous-20260927/Before/Content/GameMaps/DayNight_Lighting.umap'
if not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
report={'saved':False,'backup':str(dst),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'runtime_tested':False,'removed':[]}
for a in actors:
    if a.get_actor_label() in ['GodSpaceDistantEarth','GodSpaceDistantOcean']:
        label=a.get_actor_label()
        if not api.destroy_actor(a):raise RuntimeError('Cannot replace backdrop '+label)
        report['removed'].append(label)
a=api.spawn_actor_from_class(u.StaticMeshActor,u.Vector(-2400,-1300,0),u.Rotator(pitch=0,yaw=0,roll=0))
if not a:raise RuntimeError('Cannot create distant ocean')
a.set_actor_label('GodSpaceDistantOcean');a.set_folder_path('GodSpace/Backdrop')
a.tags=[u.Name('GodSpace.LayoutV1'),u.Name('GodSpace.VisualOnlyOcean')]
a.set_actor_tick_enabled(False)
c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_mobility(u.ComponentMobility.STATIC)
c.set_collision_profile_name('NoCollision');c.set_editor_property('generate_overlap_events',False)
c.set_cast_shadow(False);c.set_editor_property('affect_distance_field_lighting',False);c.set_editor_property('visible_in_ray_tracing',False)
c.set_editor_property('receives_decals',False)
config_file=ROOT/'configure_cloud_sea.py';config={'__file__':str(config_file)}
exec(compile(config_file.read_text(encoding='utf8'),str(config_file),'exec'),config)
report['persistent_cloud_settings']=config['apply'](sky,cloudmat)
if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Ocean map save failed')
report.update(saved=True,map=MAP,ocean_mesh=mesh.get_path_name(),cloud_material=cloudmat.get_path_name(),sea_level_cm=-150000,cloud_base_cm=-88000,cloud_top_cm=-18000,coverage_target=.8,coverage_measured=False,water_actor_tick=False,water_interactions=False)
(ROOT/'Receipts/ocean-map.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('GODSPACE_OCEAN_MAP_SAVED '+json.dumps(report))
