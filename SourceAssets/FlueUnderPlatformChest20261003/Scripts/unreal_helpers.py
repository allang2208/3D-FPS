"""Save a production-equivalent treasure prop using the existing collision Blueprint."""
import math

def spawn_preview_chest(actors,spec,pose,asset,blueprint):
    import unreal as u
    a=math.radians(pose['yaw']);x,y,z=spec['position'];o=pose['position']
    pos=u.Vector(x*math.cos(a)-y*math.sin(a)+o[0],x*math.sin(a)+y*math.cos(a)+o[1],z+o[2])
    actor=actors.spawn_actor_from_class(asset(blueprint).generated_class(),pos,
        u.Rotator(pitch=0,yaw=pose['yaw']+spec['yaw'],roll=0))
    if not actor:raise RuntimeError('Under-platform treasure authoring failed')
    actor.set_actor_label('IncineratorLine_FlueUnderPlatformTreasure')
    actor.set_folder_path('IncineratorLine/AbandonedFlueGasStation/Treasure')
    actor.set_actor_scale3d(u.Vector(*spec['scale']))
    actor.set_editor_property('tags',list(dict.fromkeys(list(actor.tags)+[u.Name(t) for t in
        ('IncineratorLine.Subject','AbandonedFlueGasStation','FlueUnderPlatformChest.Preview',
         'DungeonTreasureChest','FutureTreasureLoot','DungeonChestClaim.IncineratorLine.FlueUnderPlatform')])))
    c=actor.skeletal_mesh_component;c.set_skeletal_mesh_asset(asset(spec['skeletal_mesh']))
    c.set_mobility(u.ComponentMobility.MOVABLE);c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    for slot in range(c.get_num_materials()):
        material=c.get_material(slot)
        path=spec['material_overrides'].get(material.get_name()) if material else None
        if path:c.set_material(slot,asset(path))
    closed=asset(spec['closed_animation']);c.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE)
    c.play_animation(closed,False)
    anim=c.get_editor_property('animation_data');anim.set_editor_property('saved_position',closed.get_play_length())
    anim.set_editor_property('saved_play_rate',0.);anim.set_editor_property('saved_playing',False)
    c.set_editor_property('animation_data',anim)
    box=actor.get_component_by_class(u.BoxComponent)
    if not box:raise RuntimeError('Accepted treasure collision component unavailable')
    box.set_box_extent(u.Vector(*spec['collision_extent']),False)
    box.set_relative_location(u.Vector(*spec['collision_center']),False,False)
    box.set_collision_profile_name('BlockAll')
    return actor
