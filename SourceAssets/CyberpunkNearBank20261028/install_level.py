"""Replace only the near-bank actor and publish this revision to the formal map."""
from pathlib import Path
from datetime import datetime
import unreal as u,json,sys,shutil
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R));from design import *
def apply_upgrade(world):
    if not world or world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Wrong target map')
    assets=json.loads((R/'assets_saved.json').read_text());geo=json.loads((R/'geometry.json').read_text());layout=json.loads((R/'layout.json').read_text())
    if assets['stage']!='assets_saved':raise RuntimeError('Asset production has not finished')
    aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    meshes={k:u.load_asset(v['path']) for k,v in assets['meshes'].items()}
    classes={k:u.EditorAssetLibrary.load_blueprint_class(v['path'].split('.')[0]) for k,v in assets['blueprints'].items()}
    buildings={r['style']:u.EditorAssetLibrary.load_blueprint_class(r['blueprint']) for r in layout['buildings']}
    if not all(meshes.values()) or not all(classes.values()) or not all(buildings.values()):raise RuntimeError('Required saved assembly is unavailable')
    for name,a in actors.items():
        if name.startswith('NB28_') and not a.actor_has_tag(OWNER):raise RuntimeError('Preserve unrelated actor '+name)
    legacy=actors.get('BAY_NearBank')
    if legacy:
        current=legacy.static_mesh_component.static_mesh.get_path_name()
        expected='/Game/Props/CyberpunkBayLayered20261022/Meshes/SM_Bay_NearBank.SM_Bay_NearBank'
        if current!=expected:raise RuntimeError('Near-bank source was changed by another revision: '+current)
    installed=[]
    def place(label,cls,p,yaw=0,mesh=None,collision=False):
        a=actors.get(label)
        if not a:
            a=aa.spawn_actor_from_class(cls,u.Vector(*[v*100 for v in p]));a.set_actor_label(label);actors[label]=a
        a.modify();root=a.root_component;root.set_mobility(u.ComponentMobility.MOVABLE)
        for c in a.get_components_by_class(u.StaticMeshComponent):c.modify();c.set_mobility(u.ComponentMobility.MOVABLE)
        a.set_actor_location(u.Vector(*[v*100 for v in p]),False,False);a.set_actor_rotation(u.Rotator(pitch=0,yaw=yaw,roll=0),False);a.set_actor_scale3d(u.Vector(1,1,1))
        if mesh:a.static_mesh_component.set_static_mesh(mesh);a.static_mesh_component.set_editor_property('override_materials',[])
        a.set_editor_property('tags',[u.Name(OWNER),u.Name(label)]);a.set_folder_path('Apartment20261022/NearBank20261028');a.set_actor_tick_enabled(False);a.set_actor_enable_collision(collision)
        for c in a.get_components_by_class(u.StaticMeshComponent):
            c.set_collision_profile_name('BlockAll' if collision else 'NoCollision');c.set_editor_property('cast_shadow',True);c.set_editor_property('affect_distance_field_lighting',False);c.set_mobility(u.ComponentMobility.STATIC)
        root.set_mobility(u.ComponentMobility.STATIC);installed.append(label);return a
    for row in geo['meshes']:
        if row['key'] in ('Bollard','Drain'):continue
        place('NB28_'+row['key'],u.StaticMeshActor,row['p'],mesh=meshes[row['key']],collision=row['collision'])
    for name,row in assets['blueprints'].items():place('NB28_'+name.removeprefix('BP_NB_'),classes[name],row['origin'])
    for row in layout['buildings']:place('NB28_'+row['id'],buildings[row['style']],row['p'],row['yaw'])
    # Only retire the original near-bank actor after all replacement assemblies exist.
    if legacy:aa.destroy_actor(legacy)
    removed=[]
    for name,a in list(actors.items()):
        if name.startswith('NB28_') and name not in installed and a.actor_has_tag(OWNER):aa.destroy_actor(a);removed.append(name)
    if assets.get('materials',{}).get('BayWater'):
        a=actors['BAY_Water'];a.modify();a.static_mesh_component.modify();a.static_mesh_component.set_material(0,u.load_asset(assets['materials']['BayWater']))
    return dict(map=MAP,actors=installed,retired_original='BAY_NearBank',retired_owned=removed,counts=layout['counts'],opposite_bank_modified=False,new_maps=0,new_runtime_lights=0,new_tick_actors=0,tests_run=False,generation_method='deterministic offline shoreline and constrained assembly layout',full_city_sample_pcg_graph_executed=False)
def main():
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if ed and ed.get_game_world():raise RuntimeError('Game must finish before saving the formal map')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    disk=PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap';backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')/disk.name;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(disk,backup)
    world=u.EditorLoadingAndSavingUtils.load_map(MAP)
    result=apply_upgrade(world)
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Formal map save failed')
    result.update(stage='formal_map_saved',saved_at=datetime.now().astimezone().isoformat(),backup=str(backup),graphical_editor_started=False)
    (R/'installed.json').write_text(json.dumps(result,indent=2),encoding='utf8');print('NEAR_BANK_FORMAL_MAP_SAVED',result['counts'],len(result['actors']),flush=True)
if __name__=='__main__':main()
