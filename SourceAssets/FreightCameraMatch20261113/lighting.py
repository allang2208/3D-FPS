"""Local bounced light, anchored to the two bays; the map exposure is shared by all photographs."""
import math
import unreal as u

def run(world,row):
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    def setup(a,power,rgb,radius,contact):
        c=a.get_component_by_class(u.LightComponent)
        a.modify();c.modify()
        c.set_intensity(power);c.set_attenuation_radius(radius)
        c.set_editor_property('light_color',u.Color(r=rgb[0],g=rgb[1],b=rgb[2],a=255))
        c.set_editor_property('cast_shadows',True)
        c.set_editor_property('contact_shadow_length_in_ws',True)
        c.set_editor_property('contact_shadow_length',contact)
        c.set_editor_property('shadow_bias',.38)
        if isinstance(c,u.PointLightComponent):c.set_source_radius(18.)
        return c
    setup(actors['StationLine_AbandonedCargoWarehouse_Light_1'],row.get('packing_key',1590),(255,234,206),1100,12.)
    setup(actors['StationLine_AbandonedTransitStation_Light_2'],3800,(247,242,234),1035,13.)
    setup(actors['StationWorkshop_Light_1'],950,(241,236,225),480,7.)
    def bounce(label,eye,center,power,color,radius,width,height):
        a=actors.get(label); rotation=u.MathLibrary.find_look_at_rotation(u.Vector(*eye),u.Vector(*center))
        if not a:
            a=api.spawn_actor_from_class(u.RectLight,u.Vector(*eye),rotation)
            a.set_actor_label(label);a.set_folder_path('StationLine/ReferenceSurfaceStudy')
            a.get_component_by_class(u.RectLightComponent).set_mobility(u.ComponentMobility.MOVABLE)
        c=setup(a,power,color,radius,8.)
        c.set_source_width(width);c.set_source_height(height)
        c.set_editor_property('specular_scale',.35)
    bounce('Packing_AisleReflectedLight',(2564,251,209),(3000,373,80),row.get('packing_bounce',9.0),(250,237,219),760,175,90)
    bounce('Cart_PlatformReflectedLight',(8645,-670,217),(8414,-292,53),row.get('cart_bounce',33.0),(242,237,231),700,155,98)
