"""Install only the owned exterior replacement into the existing formal apartment."""
from pathlib import Path
from datetime import datetime
import unreal as u,json,shutil,hashlib,runpy
R=Path(__file__).resolve().parent;PROJECT=R.parents[1];MAP='/Game/GameMaps/L_CyberpunkApartment';TAG='Apartment.ExteriorFab20261025'

def apply_upgrade(world):
    if not world or world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Exterior replacement belongs to the formal apartment only')
    assets=json.loads((R/'assets_saved.json').read_text());layout=json.loads((R/'layout.json').read_text());sources=json.loads((R/'sources.json').read_text())
    if assets['stage']!='assets_saved':raise RuntimeError('Production assets must be saved before the map')
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)};aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    classes={key:u.EditorAssetLibrary.load_blueprint_class(row['path'].split('.')[0]) for key,row in assets['blueprints'].items()}
    if not all(classes.values()):raise RuntimeError('A saved production assembly cannot be loaded')
    # Resolve the exact replaced batch actors before editing this shared map.
    batches=[(g,'BAY_'+g) for g in layout['affected_groups']]+[(f'Landmark_{i}',f'AP7_BayLandmark_{i}') for i in range(5)]
    for group,label in batches:
        actor=actors[label];current=actor.static_mesh_component.static_mesh.get_path_name();old=sources['map'][label]['components'][0]['mesh']
        if current not in (old,assets['meshes'][group]):raise RuntimeError('Another skyline revision owns '+label)
    for label,actor in actors.items():
        if label.startswith('EX25_') and not actor.actor_has_tag(TAG):raise RuntimeError('An unrelated actor owns label '+label)

    def place(label,cls,p,yaw,scale,folder,identifier,shadow):
        actor=actors.get(label)
        if not actor:
            actor=aa.spawn_actor_from_class(cls,u.Vector(*p));actor.set_actor_label(label);actors[label]=actor
        actor.modify();components=actor.get_components_by_class(u.StaticMeshComponent)
        for c in components:c.modify();c.set_mobility(u.ComponentMobility.MOVABLE)
        root=actor.root_component;root.set_mobility(u.ComponentMobility.MOVABLE)
        actor.set_actor_location(u.Vector(*p),False,False);actor.set_actor_rotation(u.Rotator(pitch=0,yaw=yaw,roll=0),False);actor.set_actor_scale3d(u.Vector(scale,scale,scale))
        actor.set_editor_property('tags',[u.Name(TAG),u.Name(identifier)]);actor.set_folder_path(folder);actor.set_actor_enable_collision(False);actor.set_actor_tick_enabled(False)
        for c in components:
            if isinstance(c,u.InstancedStaticMeshComponent):c.set_editor_property('instancing_random_seed',int(hashlib.sha1((identifier+c.get_name()).encode()).hexdigest()[:7],16)+1)
            c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',shadow);c.set_editor_property('affect_distance_field_lighting',False);c.set_editor_property('visible_in_ray_tracing',False);c.set_mobility(u.ComponentMobility.STATIC)
        root.set_mobility(u.ComponentMobility.STATIC);return actor

    for group,label in batches:
        a=actors[label];a.modify();c=a.static_mesh_component;c.modify();mobility=c.get_editor_property('mobility');c.set_mobility(u.ComponentMobility.MOVABLE)
        c.set_static_mesh(u.load_asset(assets['meshes'][group]));c.set_editor_property('override_materials',[]);c.set_mobility(mobility)
        tags=list(a.tags)
        if u.Name(TAG) not in tags:a.set_editor_property('tags',tags+[u.Name(TAG)])
    installed=[];services=[]
    for row in layout['placements']:
        label='EX25_'+row['id'].replace('-','_')
        place(label,classes[row['prototype']],row['location'],row['yaw'],row['scale'],'Apartment20261022/ExteriorUpgrade20261025/'+row['zone'],row['id'],row['zone']=='primary')
        installed.append(dict(actor=label,building_id=row['id'],prototype=row['prototype'],uniform_scale=row['scale'],original_index=row['index']))
        if 'service_roof' in row:
            roof=row['service_roof'];label+='__RoofService';p=roof['center'][:];p[2]+=.5
            place(label,classes['RoofService'],p,roof['yaw'],1.2,'Apartment20261022/ExteriorUpgrade20261025/RoofService',row['id'],row['zone']=='primary');services.append(dict(actor=label,host=row['id'],support=roof))
    # Each point is on an authored V17 roof deck, clear of retained projector bases.
    landmark_roofs=[(0,[-705,1445,359.2]),(1,[-360,1507,221.2]),(2,[-1485,1462,252.2]),(3,[411,1701,242.2]),(4,[1145,2438,172])]
    for index,p in landmark_roofs:
        wp=[(-p[0]+10)*125,(p[1]-615)*125,(p[2]-90)*125+.5];label=f'EX25_Landmark_{index}_RoofService'
        place(label,classes['RoofService'],wp,0,1.25,'Apartment20261022/ExteriorUpgrade20261025/RoofService',f'Landmark_{index}',True);services.append(dict(actor=label,host=f'Landmark_{index}',support_author_metres=p))
    if 'Water' in assets.get('materials',{}):
        water=actors['BAY_Water'];water.modify();water.static_mesh_component.modify();water.static_mesh_component.set_material(0,u.load_asset(assets['materials']['Water']))
    urban=PROJECT/'SourceAssets/CyberpunkUrbanLandscape20261025'
    if (urban/'installed.json').exists():runpy.run_path(str(urban/'install_level.py'))['apply_upgrade'](world)
    return dict(map=MAP,buildings=installed,refined_landmarks=5,removed_old_buildings=layout['replaced_indices'],remainder_batches=layout['affected_groups'],roof_services=services,ad_host_building_ids=[r['id'] for r in layout['preserved_ad_hosts']],prototypes=layout['prototype_counts'],far_proxy_buildings=layout['far_proxy_buildings'],reflection='native_cube_saved' if 'Water' in assets.get('materials',{}) else 'awaiting_production_bake',new_maps=0,new_realtime_lights=0,new_tick_actors=0,new_runtime_captures=0,tests_run=False)

def main():
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('Preserve the running game')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    disk=PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap';backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')/disk.name;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(disk,backup)
    world=u.EditorLoadingAndSavingUtils.load_map(MAP);report=apply_upgrade(world)
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Formal apartment save failed')
    report.update(stage='formal_map_saved',saved_at=datetime.now().astimezone().isoformat(),backup=str(backup),map_sha256=hashlib.sha256(disk.read_bytes()).hexdigest(),interactive_editor_started=False)
    (R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('EXTERIOR_FORMAL_MAP_SAVED',len(report['buildings']),len(report['roof_services']),report['reflection'],flush=True)
if __name__=='__main__':main()
