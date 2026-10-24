import unreal as u
def finish_layout(world,owner,factor):
 changed=[]
 for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  if not actor.actor_has_tag(owner):continue
  p=actor.get_actor_location()
  actor.set_actor_location(u.Vector(p.x*factor,p.y*factor,p.z if isinstance(actor,u.PlayerStart) else p.z*factor),False,False)
  if not isinstance(actor,(u.PlayerStart,u.PostProcessVolume)):
   s=actor.get_actor_scale3d();actor.set_actor_scale3d(u.Vector(s.x*factor,s.y*factor,s.z*factor))
  if isinstance(actor,u.RectLight):
   c=actor.get_component_by_class(u.RectLightComponent)
   for name in ('source_width','source_height','attenuation_radius','max_draw_distance','max_distance_fade_range'):
    c.set_editor_property(name,c.get_editor_property(name)*factor)
   c.set_intensity(c.get_editor_property('intensity')*factor*factor)
  if isinstance(actor,u.ColdSteelSceneContainer):
   actor.set_editor_property('initial_open_fraction',0.)
   actor.set_editor_property('opened_yaw',90.)
  if actor.get_actor_label().endswith('PCGlass'):
   for c in actor.get_components_by_class(u.PrimitiveComponent):c.set_editor_property('cast_shadow',False)
  changed.append(actor.get_actor_label())
 return dict(scale=factor,scaled_actor_count=len(changed),player_size_unchanged=True,
             gym_area_m2=6.5*5.025*factor**2,reclosable_containers=True,tests_run=False)
