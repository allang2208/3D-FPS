"""Hang the shared ironwork and oak panels in the actual doorway / street frames (cm)."""
import json

import unreal as u
from author_shop import pose, require
from shop_pendants import component, remove_components

ROOT = '/Game/WorldGeneration/TemperateHills/VillageTradeSigns'
SMITH = '/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ForgeR2/SM_SmithSign'
OLD_JOINERY = '/Game/WorldGeneration/TemperateHills/VillageGunshop/Architecture/SM_Gunshop_StreetJoinery'
JOINERY = ROOT+'/SM_GunshopStreetJoinery'
HOST = 'VillageShop.HangingSign'
FIXTURE = 'VillageShop.TradeFixture'

# Position is the front of the bracket mounting plate. Its arm projects along -Y.
# The bakery's side post faces the main street. The gunshop projects past its door pentice.
MOUNTS = {
    'Bakery': ((407, 10, 303), 90, 'VillageBakery.Restored'),
    'Carpenter': ((4,-401.5,321), 0, None),
    'Tavern': ((202,-452,287), 0, None),
    'Herbalist': ((-178,-375,302), 0, None),
    'Gunshop': ((154,-23,302), 0, 'VillageGunshop.Restored'),
}
WAYPOSTS = {'Herbalist':(-2020,-296,26), 'Gunshop':(-3950,330,170)}


def hang_trade(owner, frame, shop, anchor=None, yaw=None, scale=1., waypost=False):
    loc, facing, state = MOUNTS[shop]
    x,y,z = loc if anchor is None else anchor
    heading = facing if yaw is None else yaw
    if waypost:
        state = None  # The gunshop's entire roadside actor follows the shop service state.
    def placement(px,py,pz):
        local = u.Transform(location=(px,py,pz),rotation=u.Rotator(yaw=heading),scale=(scale,)*3)
        return u.MathLibrary.compose_transforms(local,frame)
    owner.modify()
    owner.tags = list(dict.fromkeys([*map(str,owner.tags), HOST]))
    remove_components(owner,[c for c in owner.get_components_by_class(u.StaticMeshComponent)
                             if FIXTURE in map(str,c.component_tags)])
    def add(path, role, transform, moving=False):
        c = component(owner,u.StaticMeshComponent)
        c.set_mobility(u.ComponentMobility.MOVABLE if moving else u.ComponentMobility.STATIC)
        c.set_static_mesh(require(path))
        c.set_world_transform(transform,False,True)
        c.set_collision_profile_name('NoCollision')
        c.set_editor_property('generate_overlap_events',False)
        c.set_editor_property('receives_decals',False)
        c.component_tags = [FIXTURE,role,'VillageShop.NoCollision',*([state] if state else [])]
        if state:
            c.set_visibility(False)
            c.set_hidden_in_game(True)
        return c
    if waypost:
        post = add(ROOT+'/SM_TradeWaypost','VillageShop.SignSupport',frame)
        post.component_tags = [FIXTURE,'VillageShop.SignSupport']
        post.set_collision_profile_name('BlockAll')
    elif shop in ('Herbalist','Gunshop','Tavern'):
        add(ROOT+'/SM_TradeWallGround','VillageShop.SignSupport',placement(x,y,z))
    add(SMITH+'BracketR2','VillageShop.SignBracket',placement(x,y,z))
    add(SMITH+'LinksR2','VillageShop.SignLinks',placement(x,y,z-4.2*scale),True)
    panel = add(SMITH+'BoardR2','VillageShop.SignBoard',placement(x,y,z-10.35*scale),True)
    slot = panel.get_material_index('Paint')
    if slot < 0:
        raise RuntimeError('Missing Paint on '+SMITH+'BoardR2')
    panel.set_material(slot,require(ROOT+'/MI_'+shop+'Sign'))
    return dict(shop=shop,owner=owner.get_actor_label(),plate_cm=[x,y,z],yaw=heading,scale=scale,
                state=state,waypost=waypost)


def crossroads(actors, shop):
    label = 'Village_TradeWaypost_'+shop
    owner = next((a for a in actors.get_all_level_actors() if a.get_actor_label()==label),None)
    x,y,yaw = WAYPOSTS[shop]
    frame = u.Transform(location=(x,y,0),rotation=u.Rotator(yaw=yaw))
    if not owner:
        owner = actors.spawn_actor_from_class(u.Actor,frame.translation)
        owner.set_actor_label(label)
        if not owner.root_component:
            component(owner,u.SceneComponent)
    owner.modify()
    owner.root_component.set_mobility(u.ComponentMobility.STATIC)
    owner.set_actor_transform(frame,False,True)
    if shop=='Gunshop':
        owner.tags = list(dict.fromkeys([*map(str,owner.tags),'VillageGunshop.Service']))
        owner.set_actor_hidden_in_game(True)
        owner.set_actor_enable_collision(False)
    return hang_trade(owner,frame,shop,(0,-7,266),0,.76,True)


def apply(project):
    actors = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    owners = {a.get_actor_label():a for a in actors.get_all_level_actors()}
    plan = json.loads((project/'SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf-8'))
    houses = {h[0]:h for h in plan['houses']}
    owners_by_shop = dict(Bakery='Village_06_Bakery', Gunshop='Village_09_Gunshop',
                          Carpenter='Village_Carpenter_Common',Herbalist='Village_Herbalist_Common',Tavern='Village_02_Tavern')
    old = {'Village_06_Bakery':{'SM_BakerySign'}, 'Village_Carpenter_Common':{'SM_CarpenterSign'},
           'Village_Herbalist_Repaired':{'SM_TavernSign'}, 'Village_Herbalist_Ruined':{'SM_TavernSignRuined'}}
    for label, names in old.items():
        actor = owners[label]
        previous = [c for c in actor.get_components_by_class(u.StaticMeshComponent)
                    if c.static_mesh and c.static_mesh.get_name() in names]
        if previous:
            actor.modify()
            remove_components(actor,previous)
    # The previous cast sight and both rivets were baked into the door leaves and pentice.
    gun = owners[owners_by_shop['Gunshop']]
    for c in gun.get_components_by_class(u.StaticMeshComponent):
        if c.static_mesh and c.static_mesh.get_path_name().split('.')[0]==OLD_JOINERY:
            gun.modify()
            c.modify()
            c.set_static_mesh(require(JOINERY))
    placements = []
    for shop,label in owners_by_shop.items():
        owner = owners[label]
        plot = {'Carpenter':'04', 'Herbalist':'03'}.get(shop)
        frame = pose(houses[plot],0,0) if plot else owner.get_actor_transform()
        placements.append(hang_trade(owner,frame,shop))
    placements.extend(crossroads(actors,shop) for shop in WAYPOSTS)
    return placements
