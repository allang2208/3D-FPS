from pathlib import Path
import runpy,unreal as u
ROOT=Path(__file__).resolve().parent
def apply(w,row):
    runpy.run_path(str(ROOT/'distribute.py'))['apply'](w,dict(corner=2.5,raking=5.5,return_power=4.6,cart_power=30))
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    label='CartBay_EndReturn'
    pos=u.Vector(8406,-33,171);aim=u.Vector(8377,235,139);rot=u.MathLibrary.find_look_at_rotation(pos,aim)
    a=actors.get(label)
    if not a:
        api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
        a=api.spawn_actor_from_class(u.SpotLight,pos,rot);a.set_actor_label(label);a.set_folder_path('StationLine/ReferenceSurfaceStudy/CartBay')
    c=a.get_component_by_class(u.SpotLightComponent);a.modify();c.modify();c.set_mobility(u.ComponentMobility.MOVABLE)
    pos=u.Vector(8445,-10,180);aim=u.Vector(8452,235,139)
    a.set_actor_location_and_rotation(pos,u.MathLibrary.find_look_at_rotation(pos,aim),False,False)
    c.set_editor_property('intensity_units',u.LightUnits.LUMENS)
    c.set_intensity(row.get('lumens',83));c.set_attenuation_radius(480)
    c.set_inner_cone_angle(12.);c.set_outer_cone_angle(58.);c.set_source_radius(25.)
    c.set_editor_property('cast_shadows',True);c.set_editor_property('light_color',u.Color(r=246,g=245,b=242,a=255))
    c.set_editor_property('specular_scale',.13);c.set_editor_property('shadow_bias',.38)
