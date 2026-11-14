"""Low diffuse return from the platform onto the wheel faces and under-tray components."""
import unreal as u
def run(world,row):
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    label='RepairCart_PlatformFloorBounce'
    a=actors.get(label)
    if not a:
        api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
        origin=u.Vector(8538,-412,30);look=u.Vector(8412,-307,26)
        a=api.spawn_actor_from_class(u.RectLight,origin,u.MathLibrary.find_look_at_rotation(origin,look))
        a.set_actor_label(label);a.set_folder_path('StationLine/ReferenceSurfaceStudy')
    c=a.get_component_by_class(u.RectLightComponent);c.set_mobility(u.ComponentMobility.MOVABLE)
    a.modify();c.modify();c.set_attenuation_radius(245);c.set_source_width(93);c.set_source_height(23)
    c.set_intensity(1.65);c.set_editor_property('light_color',u.Color(r=249,g=234,b=218,a=255))
    c.set_editor_property('specular_scale',.14);c.set_editor_property('cast_shadows',True)
    c.set_editor_property('contact_shadow_length_in_ws',True);c.set_editor_property('contact_shadow_length',4.);c.set_editor_property('shadow_bias',.28)
