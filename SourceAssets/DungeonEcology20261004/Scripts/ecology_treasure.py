"""Existing dungeon treasure assets and one upper-gallery placement."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
BLUEPRINT='/Game/Dungeons/StationWorkshop20261003/RefineV2/Blueprints/BP_StationUpperTreasure'
TAG='Ecology.UpperPlatformTreasure'
REVISION='ecology_upper_platform_chest_20261005'

def spec():
    source=json.loads((PROJECT/'Content/ColdSteelData/treasure_chest_assets.json').read_text('utf8'))
    return dict(skeletal_mesh=source['mesh'],closed_animation=source['close'],opening_animation=source['opening'],
        material_overrides=source['materials'],collision_extent=source['collision_extent'],collision_center=source['collision_center'],
        position=[0,-1510,300.3],yaw=90,scale=[1,1,1],role='ecology_upper_platform',identity='ecology_upper_platform')

def apply(cfg):
    room=next(r for r in cfg['rooms'] if r['id']=='EcoBiosphere')
    room['props']=[p for p in room.get('props',[]) if p.get('identity')!='ecology_upper_platform']+[spec()]
    cfg['upper_platform_chest_revision']=REVISION
    return cfg

def spawn(actors,load,chest,offset_m,map_name):
    import unreal as u
    x,y,z=chest['position']
    actor=actors.spawn_actor_from_class(load(BLUEPRINT).generated_class(),
        u.Vector(x+offset_m[0]*100,y-offset_m[1]*100,z+offset_m[2]*100),
        u.Rotator(pitch=0,yaw=chest['yaw'],roll=0))
    if not actor:raise RuntimeError('Ecology treasure creation failed')
    actor.set_actor_label('EcoSubject_EcoBiosphere_UpperPlatformTreasure')
    actor.set_folder_path('Ecology/EcoBiosphere/Treasure')
    actor.set_actor_scale3d(u.Vector(*chest['scale']))
    # Subject maps have no active dungeon run. Reuse the existing independent
    # test-chest context so E can open its normal loot panel; the formal prop
    # descriptor above contains no HubTest tag or new reward rules.
    actor.set_editor_property('tags',[u.Name(t) for t in ('Ecology.Subject','EcoBiosphere',TAG,
        'DungeonTreasureChest','FutureTreasureLoot','DungeonTreasure.HubTest',
        'DungeonChestClaim.EcologySubject.'+map_name+'.UpperPlatform')])
    mesh=actor.skeletal_mesh_component
    mesh.set_skeletal_mesh_asset(load(chest['skeletal_mesh']))
    mesh.set_mobility(u.ComponentMobility.MOVABLE);mesh.set_collision_profile_name('NoCollision')
    for i in range(mesh.get_num_materials()):
        material=mesh.get_material(i);path=chest['material_overrides'].get(material.get_name()) if material else None
        if path:mesh.set_material(i,load(path))
    closed=load(chest['closed_animation']);mesh.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE)
    mesh.play_animation(closed,False)
    animation=mesh.get_editor_property('animation_data')
    animation.set_editor_property('saved_position',closed.get_play_length())
    animation.set_editor_property('saved_play_rate',0.);animation.set_editor_property('saved_playing',False)
    mesh.set_editor_property('animation_data',animation)
    box=actor.get_component_by_class(u.BoxComponent)
    if not box:raise RuntimeError('Existing treasure Blueprint has no collision component')
    box.set_box_extent(u.Vector(*chest['collision_extent']),False)
    box.set_relative_location(u.Vector(*chest['collision_center']),False,False)
    box.set_collision_profile_name('BlockAll')
    return actor
