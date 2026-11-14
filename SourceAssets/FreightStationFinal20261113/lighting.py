"""Give the north platform wall readable grazing illumination using its two existing fixtures."""
import unreal as u
def apply(w,req):
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    result=[]
    for suffix,intensity,radius in [(5,5200.,1400.),(6,4050.,1320.)]:
        a=actors['StationLine_AbandonedTransitStation_Light_'+str(suffix)]
        c=a.get_component_by_class(u.PointLightComponent);a.modify();c.modify()
        before={k:str(c.get_editor_property(k)) for k in ['intensity','attenuation_radius','light_color','cast_shadows']}
        c.set_intensity(intensity);c.set_attenuation_radius(radius)
        c.set_light_color(u.LinearColor(.94,.965,1.,1.))
        c.set_cast_shadows(True)
        c.set_editor_property('indirect_lighting_intensity',.85)
        # Existing actor, scheduler registration, fixture origin, max distance and fade stay intact.
        result.append(dict(actor=a.get_actor_label(),before=before,intensity=intensity,radius=radius))
    return result
