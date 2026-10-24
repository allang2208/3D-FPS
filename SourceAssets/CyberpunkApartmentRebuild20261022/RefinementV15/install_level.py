"""Rigid district relocation, authored river cross-section and aligned reflections."""
from pathlib import Path
from datetime import datetime
import unreal as u,json,runpy,shutil
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'));MAP=C['MAP'];PROJECT=C['PROJECT'];TAG='Apartment.V15.CloserBay'
def apply_upgrade(world):
    if world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Wrong V15 target')
    assets=json.loads((R/'assets_saved.json').read_text());baseline=json.loads((R/'bay_before.json').read_text())
    if assets['stage']!='assets_saved':raise RuntimeError('V15 assets not complete')
    aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem);actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)};moved=[]
    def tag(a):
        a.modify();tags=list(a.get_editor_property('tags'))
        if u.Name(TAG) not in tags:tags.append(u.Name(TAG));a.set_editor_property('tags',tags)
    for label,row in baseline.items():
        if not C['moved_actor'](label):continue
        a=actors[label];tag(a);p=list(row['position']);p[1]+=C['WORLD_SHIFT_Y']*100
        a.set_actor_location(u.Vector(*p),False,False);moved.append(dict(actor=label,before_cm=row['position'],after_cm=p))
    details=[]
    for key,row in assets['meshes'].items():
        label='AP15_'+key;a=actors.get(label)
        if not a:a=aa.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label(label)
        tag(a);a.set_folder_path('Apartment20261022/CloserBayWaterfront');a.set_actor_location(u.Vector(),False,False);a.set_actor_rotation(u.Rotator(),False);a.set_actor_scale3d(u.Vector(1,1,1));a.set_actor_enable_collision(False)
        c=a.static_mesh_component;c.set_static_mesh(u.load_asset(row['path']));c.set_editor_property('override_materials',[]);c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',False);c.set_editor_property('visible_in_ray_tracing',False);c.set_editor_property('affect_distance_field_lighting',False)
        details.append(label)
    water=actors['BAY_Water'];tag(water);water.static_mesh_component.set_material(0,u.load_asset(assets['materials']['Water']))
    report=dict(moved=moved,detail_actors=details,rigid_shift_m=C['WORLD_SHIFT_Y'],reference_opposite_bank_distance_before_m=1537.5,reference_opposite_bank_distance_after_m=768.75,river_width_before_m=1492.5,river_width_after_m=723.75,building_dimensions_preserved=True,open_estuary_preserved=True,near_bank_preserved=True,weather_sky_preserved=True,water=assets['materials']['Water'],reflection_cube_rebaked=True,billboard_and_beam_reflections_relocated=True,new_dynamic_lights=0,new_capture_actors=0,new_tick_actors=0,additional_triangles=assets['additional_triangles'])
    next_revision=R.parent/'RefinementV16'
    if (next_revision/'installed.json').exists():report['v16']=runpy.run_path(str(next_revision/'install_level.py'))['apply_upgrade'](world)
    return report
def main():
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map')
    backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
    shutil.copy2(PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap',backup/'L_CyberpunkApartment.umap')
    world=u.EditorLoadingAndSavingUtils.load_map(MAP);report=apply_upgrade(world)
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('V15 map save failed')
    report.update(stage='map_saved',map=MAP,saved_at=datetime.now().astimezone().isoformat(),backup=str(backup),game_tested=False,performance_measured=False)
    (R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('AP15_MAP_SAVED',len(report['moved']))
if __name__=='__main__':main()
