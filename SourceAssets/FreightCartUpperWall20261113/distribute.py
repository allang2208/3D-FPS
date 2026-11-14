"""Split the local return across the cart's wall, the visible corner and the back-facing flank."""
import unreal as u
from pathlib import Path
import runpy
def apply(w,row):
    runpy.run_path(str(Path(__file__).with_name('bay_light.py')))['apply'](w,dict(return_power=row.get('return_power',5.5),cart_power=30))
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    def light(label,eye,aim,width,height,radius,power,rgb):
        loc=u.Vector(*eye);rot=u.MathLibrary.find_look_at_rotation(loc,u.Vector(*aim));a=actors.get(label)
        if not a:
            a=api.spawn_actor_from_class(u.RectLight,loc,rot);a.set_actor_label(label);a.set_folder_path('StationLine/ReferenceSurfaceStudy/CartBay')
        a.modify();c=a.get_component_by_class(u.RectLightComponent);c.modify();c.set_mobility(u.ComponentMobility.MOVABLE)
        a.set_actor_location_and_rotation(loc,rot,False,False)
        c.set_source_width(width);c.set_source_height(height);c.set_attenuation_radius(radius);c.set_intensity(power)
        c.set_editor_property('light_color',u.Color(r=rgb[0],g=rgb[1],b=rgb[2],a=255))
        c.set_editor_property('cast_shadows',True);c.set_editor_property('specular_scale',.17);c.set_editor_property('shadow_bias',.39)
        c.set_editor_property('contact_shadow_length_in_ws',True);c.set_editor_property('contact_shadow_length',5.)
    light('CartBay_CornerReturn',(8490,-92,226),(8370,235,142),175,115,548,row.get('corner',6.5),(244,242,238))
    light('CartBay_RakingReturn',(8560,-114,205),(8317,-187,161),148,112,455,row.get('raking',7.0),(229,239,250))
