"""Idempotent installation into the existing formal apartment; exact owned replacement only."""
from pathlib import Path
from datetime import datetime
import unreal as u,json,shutil
R=Path(__file__).resolve().parent;P=R.parents[1];MAP='/Game/GameMaps/L_CyberpunkApartment';TAG='Apartment.UrbanLandscape20261025'

def apply_upgrade(world):
    if not world or world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Urban landscape belongs to the formal apartment only')
    assets=json.loads((R/'assets_saved.json').read_text(encoding='utf8'));d=json.loads((R/'layout.json').read_text(encoding='utf8'));g=json.loads((R/'geometry.json').read_text(encoding='utf8'));inputs=json.loads((R/'inputs.json').read_text(encoding='utf8'))
    if assets['stage']!='assets_saved':raise RuntimeError('Production assets are not yet saved')
    aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    for label,a in actors.items():
        if label.startswith('UL25_') and not a.actor_has_tag(TAG):raise RuntimeError('Another actor owns label '+label)
    trims=[r for r in g['meshes'] if r['kind']=='trim']
    for row in trims:
        actor=actors[row['actor']];old=inputs['actors'][row['actor']]['components'][0]['mesh'];current=actor.static_mesh_component.static_mesh.get_path_name()
        if current not in (old,assets['meshes'][row['key']]['path']):raise RuntimeError('Another mesh revision owns '+row['actor'])
    placed=[]
    def place(label,p,zone,key=None,bp=None,yaw=0,scale=1,water=False):
        a=actors.get(label)
        # Recreate this owned, non-interactive assembly so serialized component
        # instance arrays cannot retain the previous layout after a BP revision.
        if a and bp:
            if not a.actor_has_tag(TAG):raise RuntimeError('Unowned planted actor '+label)
            aa.destroy_actor(a);actors.pop(label);a=None
        if not a:
            cls=u.EditorAssetLibrary.load_blueprint_class(bp.split('.')[0]) if bp else u.StaticMeshActor
            if not cls:raise RuntimeError('Cannot load assembly '+str(bp))
            a=aa.spawn_actor_from_class(cls,u.Vector(*[v*100 for v in p]));a.set_actor_label(label);actors[label]=a
        a.modify();root=a.root_component;root.set_mobility(u.ComponentMobility.MOVABLE)
        components=a.get_components_by_class(u.StaticMeshComponent)
        for c in components:c.modify();c.set_mobility(u.ComponentMobility.MOVABLE)
        a.set_actor_location(u.Vector(*[v*100 for v in p]),False,False);a.set_actor_rotation(u.Rotator(pitch=0,yaw=yaw,roll=0),False);a.set_actor_scale3d(u.Vector(scale,scale,scale));a.set_actor_enable_collision(False);a.set_actor_tick_enabled(False)
        a.set_editor_property('tags',[u.Name(TAG),u.Name(zone),u.Name('UrbanWater' if water else 'UrbanStatic')]);a.set_folder_path('Apartment20261022/UrbanLandscape20261025/'+zone)
        if key:a.static_mesh_component.set_static_mesh(u.load_asset(assets['meshes'][key]['path']));a.static_mesh_component.set_editor_property('override_materials',[])
        for c in components:
            c.set_collision_profile_name('NoCollision');c.set_editor_property('affect_distance_field_lighting',False);c.set_editor_property('visible_in_ray_tracing',False)
            if not bp:c.set_editor_property('cast_shadow',not water and zone in ('P1','P2','P3','P4'))
            c.set_mobility(u.ComponentMobility.STATIC)
        root.set_mobility(u.ComponentMobility.STATIC);placed.append(label)
    for zone in d['zones']:place('UL25_'+zone['id']+'_Ground',zone['origin'],zone['id'],key=zone['id']+'_Ground')
    for zone,bp in assets['blueprints'].items():place('UL25_'+zone+'_Plants',bp['origin'],zone,bp=bp['path'])
    for i,row in enumerate(d['fixtures']):
        key=row['kind'];label=f"UL25_{row['zone']}_{key}_{i:03d}";place(label,row['p'],row['zone'],key=key,yaw=row['yaw'],scale=row['scale'])
        if key+'_Water' in assets['meshes']:place(label+'_Water',row['p'],row['zone'],key=key+'_Water',yaw=row['yaw'],scale=row['scale'],water=True)
    # New vegetation is placed before trimming the obsolete coarse crowns.
    for row in trims:
        a=actors[row['actor']];a.modify();c=a.static_mesh_component;c.modify();mobility=c.get_editor_property('mobility');c.set_mobility(u.ComponentMobility.MOVABLE);c.set_static_mesh(u.load_asset(assets['meshes'][row['key']]['path']));c.set_editor_property('override_materials',[]);c.set_mobility(mobility)
        if not a.actor_has_tag(TAG):a.set_editor_property('tags',list(a.tags)+[u.Name(TAG)])
    # Only retired objects from this owned batch can be removed on future updates.
    for label,a in actors.items():
        if label.startswith('UL25_') and a.actor_has_tag(TAG) and label not in placed:aa.destroy_actor(a)
    if 'BayWater' in assets['materials']:
        water=actors['BAY_Water'];water.modify();water.static_mesh_component.modify();water.static_mesh_component.set_material(0,u.load_asset(assets['materials']['BayWater']))
    return dict(map=MAP,counts=d['counts'],revision=d.get('revision','initial'),relocation=d.get('relocation',{}),actors=placed,replaced_meshes=[r['actor'] for r in trims],new_maps=0,new_runtime_lights=0,new_tick_actors=0,new_runtime_captures=0,tests_run=False,reflection='native_cube_saved' if assets.get('reflection_texture') else 'pending_production_bake')

def main():
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('Finish the authorized end-play step before installing')
    world=editor.get_editor_world() if editor else None
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve existing unsaved map changes')
    disk=P/'Content/GameMaps/L_CyberpunkApartment.umap';backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')/disk.name;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(disk,backup)
    if not world or world.get_path_name().split('.')[0]!=MAP:world=u.EditorLoadingAndSavingUtils.load_map(MAP)
    result=apply_upgrade(world)
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Cannot save formal apartment')
    result.update(stage='formal_map_saved',saved_at=datetime.now().astimezone().isoformat(),backup=str(backup),interactive_editor_started=False)
    (R/'installed.json').write_text(json.dumps(result,indent=2),encoding='utf8');print('URBAN_FORMAL_MAP_SAVED',len(result['actors']),result['counts'],flush=True)
if __name__=='__main__':main()
