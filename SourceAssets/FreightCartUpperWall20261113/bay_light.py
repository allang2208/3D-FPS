from pathlib import Path
import unreal as u
def apply(w,row):
    lookup={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    def color(c,three):
        c.set_editor_property('light_color',u.Color(r=three[0],g=three[1],b=three[2],a=255))
    # The existing reflected source is local to this cart, so leave station fixtures and exposure alone.
    a=lookup['Cart_PlatformReflectedLight'];a.modify()
    c=a.get_component_by_class(u.RectLightComponent);c.modify()
    color(c,(244,246,247));c.set_intensity(row.get('cart_power',30))
    label='CartBay_LeftWallReturn';a=lookup.get(label)
    eye=u.Vector(8518,-36,189);aim=u.Vector(8369,160,119)
    rotation=u.MathLibrary.find_look_at_rotation(eye,aim)
    if not a:
        a=api.spawn_actor_from_class(u.RectLight,eye,rotation);a.set_actor_label(label)
        a.set_folder_path('StationLine/ReferenceSurfaceStudy/CartBay')
    c=a.get_component_by_class(u.RectLightComponent);a.modify();c.modify();c.set_mobility(u.ComponentMobility.MOVABLE)
    a.set_actor_location_and_rotation(eye,rotation,False,False)
    c.set_source_width(182);c.set_source_height(109);c.set_attenuation_radius(565)
    c.set_intensity(row.get('return_power',31));color(c,(232,242,251))
    c.set_editor_property('cast_shadows',True);c.set_editor_property('shadow_bias',.37)
    c.set_editor_property('contact_shadow_length_in_ws',True);c.set_editor_property('contact_shadow_length',6.0)
    c.set_editor_property('specular_scale',.32)
