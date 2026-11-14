"""Wall toe dust and moisture tracks aligned to the original concrete planes."""
import unreal as u
def run(world,row):
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    root='/Game/SceneTests/FreightStationUnifiedPatina20261111/Materials/MI_'
    placements=[
        ('Packing_WallMoisture', (2950,485.78,146),90,(1.3,54,133),'LeakSoft'),
        ('Packing_LowerWallDust',(2884,485.81,37),90,(1.3,134,35),'DustWall'),
        ('Cart_WallSeepage',(8317.24,-337,141),180,(1.2,61,132),'LeakSoft'),
        ('Cart_LowerServiceWall',(8317.26,-256,44),180,(1.2,143,41),'DampWall')]
    for label,location,yaw,size,mat in placements:
        a=actors.get(label)
        if not a:
            a=api.spawn_actor_from_class(u.DecalActor,u.Vector(*location),u.Rotator(yaw=yaw))
            a.set_actor_label(label);a.set_folder_path('StationLine/ReferenceSurfaceStudy')
        c=a.get_component_by_class(u.DecalComponent);c.modify()
        c.set_editor_property('decal_size',u.Vector(*size));c.set_editor_property('sort_order',3)
        c.set_editor_property('fade_screen_size',.001);c.set_decal_material(u.load_asset(root+mat))
