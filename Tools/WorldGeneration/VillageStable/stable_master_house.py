"""Author the Normandy single-storey Stablemaster House inside the expanded enclosure and relocate BP_Stablemaster."""
from collections import defaultdict
import math
from pathlib import Path
import sys
import unreal as ue

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / 'AbandonedVillage')]
from room_daylight import RESIDENTIAL_DAYLIGHT, apply_daylight
from shop_staff_light import WICK, configure
from stable_actors import ASSEMBLY, add_instances, label_stable
from stable_lighting import (
    CHAIN_MESH,
    add_lantern_and_light,
    append_pendant_hardware,
    append_wall_bracket_hardware,
    make_chain_ism,
    make_iron_hardware_ism,
)

TAG = 'VillageStable.MasterHouse'
PREFIX = 'Village_Stable_MasterHouse_'

# House centre in village-local centimetres. Walls span +-290 cm (5.8 m x 5.8 m Normandy 2x2 bay).
# Footprint sits inside the expanded southwest paddock (X: 13.3..19.7 m, Y: 38.0..44.4 m):
#   - 3.8 m east of West Fence (X=9.5 m), clear of WestPaddockGate inward swing (X=9.5..11.8 m)
#   - 4.8 m south of North Paddock Fence (Y=33.2 m)
#   - 1.8 m north of South Rear Fence (Y=46.2 m)
#   - 10.0 m west of Watering Trough & Barn, framing a generous open central paddock.
HOUSE_CX = 1650.0
HOUSE_CY = 4120.0
FOUNDATION_LIFT = 24.0
FLOOR_TOP_Z = 4.0 + FOUNDATION_LIFT   # +28.0 cm elevated wood deck above yard soil
WALL_Z = 129.0 + FOUNDATION_LIFT      # +153.0 cm; door sill sits cleanly at Z ~ 30 cm (+2 cm above floor)

NORMANDY = '/Game/UnrealNormandy/StaticMeshes/'
HILLS = '/Game/WorldGeneration/TemperateHills/'
TAVERN = '/Game/WorldGeneration/VillageTavern/'
CARPENTER_DECK = HILLS + 'VillageCarpenter/Structure/SM_CarpenterDeck'

MESH_PATHS = {
    'StoneWall': NORMANDY + 'SM_H_StoneWall_00A',
    'OldWall': NORMANDY + 'SM_H_OldWall_00A',
    'DoorWall': NORMANDY + 'SM_H_OldWall_Door_00A',
    'WindowWall': NORMANDY + 'SM_H_OldWall_Window_00A',
    'Corner': NORMANDY + 'SM_H_WallCorner_00A',
    'Gable': NORMANDY + 'SM_H_OldWall_Triangle_00A',
    'DeckWest': CARPENTER_DECK + 'West',
    'DeckEast': CARPENTER_DECK + 'East',
    'DeckSpliced': CARPENTER_DECK + 'SplicedPlank',
    'Roof': NORMANDY + 'SM_Roof_00A',
    'RoofEnd': NORMANDY + 'SM_RoofEnd_00A',
    'WindowFrame': NORMANDY + 'SM_Window_Frame_00A',
    'ShutterL': NORMANDY + 'SM_Window_Shutter_01A',
    'ShutterR': NORMANDY + 'SM_Window_Shutter_00A',
    'DoorLeaf': TAVERN + 'Inn/SM_InnRoomDoor',
    'Plank': NORMANDY + 'SM_HW_Plank_01A',
    'Lantern': NORMANDY + 'SM_Props_Lantern_02A',
    'Flagstone': HILLS + 'OldChapel/Meshes/SM_ChapelYardPathStone',
    'OakTable': HILLS + 'VillageBlacksmith/ArtPassR2/Meshes/SM_VillageOakTable',
    'OakStool': HILLS + 'VillageBlacksmith/ArtPassR2/Meshes/SM_VillageOakStool',
    'OakShelf': HILLS + 'VillageBlacksmith/ArtPassR2/Meshes/SM_VillageOakShelf',
    'TimberBed': HILLS + 'VillageBlacksmith/ArtPassR2/Meshes/SM_VillageTimberBed',
    'Chest': HILLS + 'VillageCarpenter/InteriorR1/SM_CarpenterJoinersChest',
    'ChestLid': HILLS + 'VillageCarpenter/InteriorR1/SM_CarpenterJoinersChestLid',
    'Tools': HILLS + 'VillageCarpenter/Props/SM_CarpenterTools',
    'AleCask': TAVERN + 'Service/SM_TavernAleCask',
    'GrainSack': HILLS + 'VillageBakery/Grain/SM_BakeryGrainSack',
    'TiedSack': HILLS + 'VillageWindmill/Yard/Meshes/SM_MillTiedSack',
    'Measure': HILLS + 'VillageWindmill/Yard/Meshes/SM_MillMeasure',
    'ShoeingWork': HILLS + 'VillageShopRest/SM_SmithShoeingWork',
    'WindowPot': HILLS + 'VillageHerbalist/Props/SM_HerbalistWindowPot',
    'SaddleStand': HILLS + 'VillageStable/PropsR43/SM_Stable_SaddleStand',
    'TackWallRack': HILLS + 'VillageStable/PropsR43/SM_Stable_TackWallRack',
}

TRADE_ROOT = HILLS + 'VillageTradeSigns'
SMITH_SIGN = HILLS + 'VillageBlacksmith/ForgeR2/SM_SmithSign'


def _install_cabin_trade_sign(actors):
    """Hang the shared village wrought-iron bracket & MI_StableSign oak shield beside the cabin porch."""
    label = PREFIX + 'TradeSign'
    host = label_stable(actors.spawn_actor_from_class(ue.Actor, ue.Vector(HOUSE_CX, HOUSE_CY, 0.0)), label, [ASSEMBLY, TAG])
    subs = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
    data = ue.SubobjectDataBlueprintFunctionLibrary
    parent = subs.k2_gather_subobject_data_for_instance(host)[0]
    if not host.root_component:
        h, err = subs.add_new_subobject(ue.AddNewSubobjectParams(parent_handle=parent, new_class=ue.SceneComponent))
        if not data.get_associated_object(data.get_data(h)):
            raise RuntimeError(str(err))
    host.root_component.set_mobility(ue.ComponentMobility.STATIC)

    sx, sy, sz = HOUSE_CX + 22.0, HOUSE_CY - 296.0, 266.0 + FOUNDATION_LIFT
    sc = 0.76
    host.set_actor_location(ue.Vector(sx, sy, sz), False, True)

    def add_part(path, dz=0.0, moving=False):
        h, err = subs.add_new_subobject(ue.AddNewSubobjectParams(parent_handle=parent, new_class=ue.StaticMeshComponent))
        mc = data.get_associated_object(data.get_data(h))
        if not mc:
            raise RuntimeError(str(err))
        mc.set_mobility(ue.ComponentMobility.MOVABLE if moving else ue.ComponentMobility.STATIC)
        mc.set_static_mesh(_load(path))
        mc.set_relative_location(ue.Vector(0.0, 0.0, dz), False, True)
        mc.set_relative_scale3d(ue.Vector(sc, sc, sc))
        mc.set_collision_profile_name('NoCollision')
        mc.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
        mc.set_editor_property('receives_decals', False)
        return mc

    add_part(TRADE_ROOT + '/SM_TradeWallGround', 0.0, False)
    add_part(SMITH_SIGN + 'BracketR2', 0.0, False)
    add_part(SMITH_SIGN + 'LinksR2', -4.2 * sc, True)
    panel = add_part(SMITH_SIGN + 'BoardR2', -10.35 * sc, True)
    paint_slot = panel.get_material_index('Paint')
    if paint_slot < 0:
        raise RuntimeError('Missing Paint slot on ' + SMITH_SIGN + 'BoardR2')
    panel.set_material(paint_slot, _load(TRADE_ROOT + '/MI_StableSign'))
    return dict(actor=label, world_cm=[sx, sy, sz], scale=sc, material=TRADE_ROOT + '/MI_StableSign')


def _load(path):
    obj = ue.load_asset(path)
    if not obj:
        raise RuntimeError('Missing stablemaster house asset: ' + path)
    return obj


def _install_cabin_door(actors, door_mesh, existing_door):
    # Matches SL_Packed_House_TypeA_00A opening inside SM_H_OldWall_Door_00A at local (-148.5, -290, WALL_Z).
    # Opening center is at local (-146.0, -294.9), width 144.8 cm, height 221.7 cm.
    # SM_InnRoomDoor has width along local Y (103.8 cm) and height along Z (216.0 cm), matching
    # AColdSteelDoor::AlignGeometry() natively. Scale actor Y/Z to fit the Normandy opening cleanly.
    door_x = HOUSE_CX - 146.0
    door_y = HOUSE_CY - 294.9
    door_z = FLOOR_TOP_Z + 2.0  # 2 cm clearance above wooden floor

    label = PREFIX + 'Door'
    rot = ue.Rotator(yaw=90.0)  # Local +X points +Y (inward), local +Y points -X (west jamb).
    pos = ue.Vector(door_x, door_y, door_z)
    bounds = door_mesh.get_bounding_box()
    native_w = float(bounds.max.y - bounds.min.y)  # 103.8 cm
    native_h = float(bounds.max.z - bounds.min.z)  # 216.0 cm
    scale = ue.Vector(1.0, 141.5 / native_w, 219.5 / native_h)

    actor = existing_door
    if actor is None:
        actor = label_stable(
            actors.spawn_actor_from_class(ue.ColdSteelDoor, pos, rot),
            label,
            [ASSEMBLY, TAG, 'Door.OpenInwardOnly'],
        )
    actor.modify()
    actor.set_actor_transform(ue.Transform(location=pos, rotation=rot, scale=scale), False, True)
    actor.set_editor_property('tags', [ASSEMBLY, TAG, 'Door.OpenInwardOnly'])
    for field, value in (
        ('hinge_on_positive_y', True),  # +Y local = west jamb (-X world), swings inward (+Y) cleanly along west wall
        ('open_angle_degrees', 95.0),
        ('open_seconds', 0.72),
        ('auto_close_seconds', 0.0),
    ):
        actor.set_editor_property(field, value)

    parts = {c.get_name(): c for c in actor.get_components_by_class(ue.SceneComponent)}
    parts['DoorFrame'].set_static_mesh(None)
    parts['DoorFrame'].set_collision_profile_name('NoCollision')

    leaf = parts['DoorLeaf']
    leaf.modify()
    leaf.set_static_mesh(door_mesh)
    leaf.set_collision_profile_name('BlockAll')
    leaf.set_relative_rotation(ue.Rotator(yaw=180.0), False, True)
    hinge = native_w * 0.5
    parts['DoorHinge'].set_relative_location(ue.Vector(0.0, hinge, 0.0), False, True)
    leaf.set_relative_location(ue.Vector(
        -(bounds.min.x + bounds.max.x) * 0.5,
        -hinge - (bounds.min.y + bounds.max.y) * 0.5,
        -bounds.min.z,
    ), False, True)
    return dict(actor=label, location_cm=[door_x, door_y, door_z], opening_width_cm=141.5, leaf_mesh=door_mesh.get_path_name())


def _install_lights(actors, lantern_mesh, wick):
    host_label = PREFIX + 'Lights'
    host = label_stable(actors.spawn_actor_from_class(ue.Actor, ue.Vector(HOUSE_CX, HOUSE_CY, 0.0)), host_label, [ASSEMBLY, TAG])
    subs = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
    data = ue.SubobjectDataBlueprintFunctionLibrary
    parent = subs.k2_gather_subobject_data_for_instance(host)[0]
    if not host.root_component:
        h, err = subs.add_new_subobject(ue.AddNewSubobjectParams(parent_handle=parent, new_class=ue.SceneComponent))
        if not data.get_associated_object(data.get_data(h)):
            raise RuntimeError(str(err))
    host.root_component.set_mobility(ue.ComponentMobility.STATIC)
    host.set_actor_location(ue.Vector(HOUSE_CX, HOUSE_CY, 0.0), False, True)

    chain_mesh = _load(CHAIN_MESH)
    chain_box = chain_mesh.get_bounding_box()
    iron_poses, chain_poses = [], []
    placed = []

    # 1. Single central interior pendant (removed second interior lamp per StableLightsR50).
    # Anchored cleanly onto the middle ceiling beam soffit (lx=0, Z=300.0 cm), 210 cm headroom above wood deck.
    int_lx, int_ly = 0.0, 10.0
    int_bottom_z, int_h, int_soffit_z = 238.0, 34.0, 276.0 + FOUNDATION_LIFT  # 300.0 cm
    append_pendant_hardware(iron_poses, chain_poses, chain_box, int_lx, int_ly, int_soffit_z, int_bottom_z + int_h, yaw_deg=0.0)
    int_info = add_lantern_and_light(
        subs, data, parent, lantern_mesh, wick,
        int_lx, int_ly, int_bottom_z, int_h, yaw_deg=0.0,
        level=0.95, draw_dist=2000.0,
    )
    placed.append(dict(
        name='InteriorMain',
        mount='ceiling_beam_pendant',
        world_cm=[HOUSE_CX + int_lx, HOUSE_CY + int_ly, int_info['light_z']],
        lantern_z_cm=[int_info['bottom_z'], int_info['top_z']],
        soffit_z_cm=int_soffit_z,
        max_draw_distance=2000.0,
    ))

    # 2. Exterior porch wall-bracket lantern beside north doorway (clear of DoorWall Y=-307.7 and TradeSign X=+22).
    ext_lx, ext_wall_y, ext_reach = -42.0, -307.7, 27.3  # hangs at ly = -335.0
    ext_arm_z, ext_bottom_z, ext_h = 282.0, 235.0, 33.0
    ext_hx, ext_hy = append_wall_bracket_hardware(
        iron_poses, chain_poses, chain_box,
        ext_lx, ext_wall_y, 0.0, -1.0, ext_arm_z, ext_reach, ext_bottom_z + ext_h, brace_drop_cm=16.0,
    )
    ext_info = add_lantern_and_light(
        subs, data, parent, lantern_mesh, wick,
        ext_hx, ext_hy, ext_bottom_z, ext_h, yaw_deg=0.0,
        level=0.95, draw_dist=2400.0,
    )
    placed.append(dict(
        name='ExteriorPorch',
        mount='wall_bracket',
        world_cm=[round(HOUSE_CX + ext_hx, 1), round(HOUSE_CY + ext_hy, 1), ext_info['light_z']],
        lantern_z_cm=[ext_info['bottom_z'], ext_info['top_z']],
        wall_y_cm=round(HOUSE_CY + ext_wall_y, 1),
        max_draw_distance=2400.0,
    ))

    iron_ism = make_iron_hardware_ism(subs, data, parent, cull_distance=2600.0)
    iron_ism.add_instances(iron_poses, False, False, False)
    chain_ism = make_chain_ism(subs, data, parent, cull_distance=2600.0)
    chain_ism.add_instances(chain_poses, False, False, False)
    return placed


def _install_daylight(actors):
    label = 'Village_InteriorVision_StableMasterHouse'
    existing = next((a for a in actors.get_all_level_actors() if a.get_actor_label() == label), None)
    room = existing or actors.spawn_actor_from_class(ue.BuildingDaylight, ue.Vector(HOUSE_CX, HOUSE_CY, FLOOR_TOP_Z))
    room.modify()
    room.set_actor_label(label)
    room.set_folder_path('Village/EastGateStable')
    room.set_editor_property('tags', [ASSEMBLY, TAG])
    room.set_actor_transform(ue.Transform(location=(HOUSE_CX, HOUSE_CY, FLOOR_TOP_Z)), False, True)
    room.set_editor_property('room_minimum', ue.Vector(-265.0, -265.0, 0.0))
    room.set_editor_property('room_maximum', ue.Vector(265.0, 265.0, 310.0))
    apply_daylight(room, RESIDENTIAL_DAYLIGHT)
    return label


def _relocate_stablemaster(actors):
    label = 'Village_Stable_Stablemaster'
    tag = 'VillageStable.Stablemaster'
    found = [a for a in actors.get_all_level_actors() if tag in map(str, a.tags) or a.get_actor_label() == label]
    if len(found) != 1:
        raise RuntimeError(f'Expected 1 stablemaster NPC, found {len(found)}')
    npc = found[0]
    cls = npc.get_class()
    cdo = ue.get_default_object(cls)
    bounds = cdo.mesh.skeletal_mesh_asset.get_imported_bounds()

    # Stand naturally inside the cabin beside/behind the oak reception desk,
    # looking directly toward the NW doorway (HOUSE_CX-146, HOUSE_CY-295).
    npc_x = HOUSE_CX + 45.0   # 1695 cm
    npc_y = HOUSE_CY + 95.0   # 4215 cm
    door_x = HOUSE_CX - 146.0
    door_y = HOUSE_CY - 295.0
    facing = math.degrees(math.atan2(door_y - npc_y, door_x - npc_x))  # ~ -115.8 deg (NW toward door)
    origin_z = FLOOR_TOP_Z - cdo.mesh.relative_location.z - (bounds.origin.z - bounds.box_extent.z)
    origin = ue.Vector(npc_x, npc_y, origin_z)
    rot = ue.Rotator(yaw=facing)

    npc.modify()
    npc.set_actor_location_and_rotation(origin, rot, False, True)
    npc.set_folder_path('Village/EastGateStable')
    return dict(
        actor=label,
        location_cm=[round(npc_x, 1), round(npc_y, 1), round(float(origin_z), 1)],
        feet_z_cm=FLOOR_TOP_Z,
        facing_deg=round(facing, 1),
    )


def install_stable_master_house(actors):
    existing_door = None
    for actor in list(actors.get_all_level_actors()):
        tags = set(map(str, actor.tags))
        if TAG in tags:
            if actor.get_actor_label() == PREFIX + 'Door' and isinstance(actor, ue.ColdSteelDoor):
                existing_door = actor
                continue
            if actor.get_actor_label() == 'Village_InteriorVision_StableMasterHouse':
                continue
            actors.destroy_actor(actor)

    meshes = {k: _load(v) for k, v in MESH_PATHS.items()}
    boxes = {k: m.get_bounding_box() for k, m in meshes.items()}
    wick = _load(WICK)
    groups = defaultdict(list)
    tags = [ASSEMBLY, TAG]

    def put_raw(role, lx, ly, lz, yaw=0.0, scale=(1.0, 1.0, 1.0), solid=True):
        groups[role, solid].append(ue.Transform(
            location=(HOUSE_CX + lx, HOUSE_CY + ly, lz),
            rotation=ue.Rotator(yaw=yaw),
            scale=scale,
        ))

    def fit(role, lx, ly, z_bottom, w, d, h, yaw=0.0, solid=True):
        b = boxes[role]
        base = ue.Vector((b.min.x + b.max.x) * 0.5, (b.min.y + b.max.y) * 0.5, b.min.z)
        frame = ue.Transform(
            location=(HOUSE_CX + lx, HOUSE_CY + ly, z_bottom),
            rotation=ue.Rotator(yaw=yaw),
            scale=ue.Vector(w, d, h) / (b.max - b.min),
        )
        groups[role, solid].append(ue.MathLibrary.compose_transforms(ue.Transform(location=-base), frame))

    def place_on(role, lx, ly, z_bottom, yaw=0.0, scale=1.0, solid=True):
        b = boxes[role]
        base = ue.Vector((b.min.x + b.max.x) * 0.5, (b.min.y + b.max.y) * 0.5, b.min.z)
        frame = ue.Transform(
            location=(HOUSE_CX + lx, HOUSE_CY + ly, z_bottom),
            rotation=ue.Rotator(yaw=yaw),
            scale=(scale, scale, scale),
        )
        groups[role, solid].append(ue.MathLibrary.compose_transforms(ue.Transform(location=-base), frame))

    # --- 1. Elevated Stone Foundation Plinth (Z = -18..+26.5 cm) & Shop Wooden Plank Deck ---
    # Reuses SM_CarpenterDeckWest/East/SplicedPlank (shared by Carpenter, Herbalist & Tavern).
    # Each scanned tile has nominal 300x300 cm bay pitch (staggered plank ends reach +-60 cm across
    # the centre splice), so scale by 290/300 to span the exact 580x580 cm interior wall-to-wall.
    deck_b = boxes['DeckWest']
    deck_h = float(deck_b.max.z - deck_b.min.z)
    tile_sx = 290.0 / 300.0
    tile_sy = 290.0 / 300.0
    tile_sz = 20.0 / deck_h
    deck_z_origin = FLOOR_TOP_Z - float(deck_b.max.z) * tile_sz

    def add_deck_pair(cy, reversed_pair):
        yaw = 180.0 if reversed_pair else 0.0
        west_x = 145.0 if reversed_pair else -145.0
        east_x = -145.0 if reversed_pair else 145.0
        west_tf = ue.Transform(
            location=(HOUSE_CX + west_x, HOUSE_CY + cy, deck_z_origin),
            rotation=ue.Rotator(yaw=yaw),
            scale=(tile_sx, tile_sy, tile_sz),
        )
        east_tf = ue.Transform(
            location=(HOUSE_CX + east_x, HOUSE_CY + cy, deck_z_origin),
            rotation=ue.Rotator(yaw=yaw),
            scale=(tile_sx, tile_sy, tile_sz),
        )
        groups['DeckWest', True].append(west_tf)
        groups['DeckEast', True].append(east_tf)
        # Spliced oak infill plank shares the exact local origin & bounds of DeckEast (no collision).
        groups['DeckSpliced', False].append(east_tf)

    add_deck_pair(-145.0, reversed_pair=False)
    add_deck_pair(145.0, reversed_pair=True)

    # Full perimeter dressed Normandy stone foundation plinth skirting from Z = -18 cm to +26.5 cm
    # (strictly 1.5 cm below FLOOR_TOP_Z so stone never pokes through wood planks, seated around exterior wall bases).
    plinth_z0 = -18.0
    plinth_h = FLOOR_TOP_Z - plinth_z0 - 1.5  # 44.5 cm tall -> top at +26.5 cm
    # North & South perimeter courses (4 dressed stone plinth blocks per wall, exterior face at +-329 cm)
    for px in (-225.0, -75.0, 75.0, 225.0):
        fit('Flagstone', px, -308.0, plinth_z0, 166.0, 42.0, plinth_h, yaw=0.0, solid=True)
        fit('Flagstone', px, 308.0, plinth_z0, 166.0, 42.0, plinth_h, yaw=180.0, solid=True)
    # West & East perimeter courses
    for py in (-225.0, -75.0, 75.0, 225.0):
        fit('Flagstone', -308.0, py, plinth_z0, 166.0, 42.0, plinth_h, yaw=-90.0, solid=True)
        fit('Flagstone', 308.0, py, plinth_z0, 166.0, 42.0, plinth_h, yaw=90.0, solid=True)
    # Four heavy corner plinth stones capping the perimeter skirt (top +27.0 cm)
    for cx, cy, cyaw in ((-308.0, -308.0, 0.0), (308.0, -308.0, 90.0), (-308.0, 308.0, -90.0), (308.0, 308.0, 180.0)):
        fit('Flagstone', cx, cy, plinth_z0, 62.0, 62.0, plinth_h + 0.5, yaw=cyaw, solid=True)

    # Two solid dressed-stone entrance steps outside the north doorway (-146, -294.9):
    # Upper threshold landing (top +27.5 cm) -> Lower step (top +14.0 cm) -> Yard flagstones (+2.5 cm).
    fit('Flagstone', -146.0, -330.0, -14.0, 168.0, 66.0, 41.5, yaw=0.0, solid=True)
    fit('Flagstone', -146.0, -382.0, -14.0, 188.0, 58.0, 28.0, yaw=2.0, solid=True)

    # --- 2. Ground-Storey Walls (exact SL_Packed_House_TypeA_00A 2x2 Normandy modular spacing) ---
    # North Front Wall (Y = -290, faces -Y toward yard & gates)
    put_raw('DoorWall', -148.5, -290.0, WALL_Z, yaw=0.0, solid=True)
    put_raw('WindowWall', 151.5, -290.0, WALL_Z, yaw=0.0, solid=True)

    # South Rear Wall (Y = +290, solid weathered Normandy stone)
    put_raw('StoneWall', -148.5, 290.0, WALL_Z, yaw=180.0, solid=True)
    put_raw('StoneWall', 151.5, 290.0, WALL_Z, yaw=180.0, solid=True)

    # East Wall (X = +290, faces +X toward paddock & horse stalls: north window + south stone)
    put_raw('WindowWall', 290.0, -150.0, WALL_Z, yaw=90.0, solid=True)
    put_raw('StoneWall', 290.0, 150.0, WALL_Z, yaw=90.0, solid=True)

    # West Wall (X = -290, faces -X toward West Paddock Gate: north window + south stone)
    put_raw('WindowWall', -290.0, -150.0, WALL_Z, yaw=-90.0, solid=True)
    put_raw('StoneWall', -290.0, 150.0, WALL_Z, yaw=-90.0, solid=True)

    # 4 Stone Quoin Corners (matching TypeA_00A exact rotations)
    for cx, cy, cyaw in (
        (-280.0, -280.0, 180.0),
        (281.5, -280.0, -90.0),
        (-280.0, 280.0, 90.0),
        (281.5, 280.0, 0.0),
    ):
        put_raw('Corner', cx, cy, WALL_Z, yaw=cyaw, solid=True)

    # --- 3. Windows & Open Shutters (3 windows: North-East, East-North, West-North) ---
    win_z = WALL_Z + 30.3  # exact TypeA_00A window vertical offset
    # North-East window (faces -Y; shutters folded outward open against exterior wall)
    put_raw('WindowFrame', 154.0, -290.0, win_z, yaw=0.0, scale=(0.96, 1.0, 1.0), solid=True)
    put_raw('ShutterR', 198.0, -297.0, win_z - 0.8, yaw=-25.0, solid=False)
    put_raw('ShutterL', 108.0, -297.0, win_z - 0.8, yaw=25.0, solid=False)
    # East-North window (faces +X)
    put_raw('WindowFrame', 290.0, -147.5, win_z, yaw=90.0, scale=(0.96, 1.0, 1.0), solid=True)
    put_raw('ShutterR', 297.0, -103.5, win_z - 0.8, yaw=65.0, solid=False)
    put_raw('ShutterL', 297.0, -193.5, win_z - 0.8, yaw=115.0, solid=False)
    # West-North window (faces -X)
    put_raw('WindowFrame', -290.0, -152.5, win_z, yaw=-90.0, scale=(0.96, 1.0, 1.0), solid=True)
    put_raw('ShutterR', -297.0, -196.5, win_z - 0.8, yaw=-115.0, solid=False)
    put_raw('ShutterL', -297.0, -106.5, win_z - 0.8, yaw=-65.0, solid=False)

    # --- 4. Gables & Pitched Normandy Slate Roof (East-West ridge parallel to Stable Barn) ---
    gable_z = WALL_Z + 280.0
    for gx, gy, gyaw in (
        (-288.5, 130.0, -90.0),
        (-288.5, -130.0, 90.0),
        (285.0, 130.0, -90.0),
        (285.0, -130.0, 90.0),
    ):
        put_raw('Gable', gx, gy, gable_z, yaw=gyaw, scale=(0.9, 0.9, 0.9), solid=True)

    roof_z = WALL_Z + 300.0
    put_raw('Roof', -148.5, 150.0, roof_z, yaw=0.0, solid=True)
    put_raw('RoofEnd', 151.5, 150.0, roof_z, yaw=0.0, solid=True)
    put_raw('Roof', 151.5, -150.0, roof_z, yaw=180.0, solid=True)
    put_raw('RoofEnd', -148.5, -150.0, roof_z, yaw=180.0, solid=True)

    # --- 5. Interior Ceiling Beams & Eave Timber Trim ---
    for bx in (-145.0, 0.0, 145.0):
        fit('Plank', bx, 0.0, 276.0 + FOUNDATION_LIFT, 560.0, 18.0, 22.0, yaw=90.0, solid=False)
    # Exterior eave fascia timber lintels over north front wall
    fit('Plank', 0.0, -284.0, 272.0 + FOUNDATION_LIFT, 560.0, 12.0, 20.0, yaw=0.0, solid=False)

    # --- 6. Entry Flagstones Leading from North Entrance Steps (-146, -408) into Yard ---
    for fx, fy, fw, fd, fyaw in [
        (-148.0, -432.0, 88.0, 52.0, -5.0),
        (-140.0, -486.0, 74.0, 46.0, 11.0),
        (-212.0, -456.0, 62.0, 40.0, -16.0),
        (-284.0, -434.0, 66.0, 42.0, 7.0),
        (-362.0, -414.0, 64.0, 38.0, -11.0),
        (-446.0, -392.0, 60.0, 38.0, 8.0),
        (-535.0, -360.0, 64.0, 40.0, -6.0),
        (-620.0, -335.0, 68.0, 44.0, 5.0),
        (-74.0, -494.0, 56.0, 38.0, -14.0),
        (5.0, -504.0, 58.0, 38.0, 10.0),
    ]:
        fit('Flagstone', fx, fy, -3.5, fw, fd, 6.0, yaw=fyaw, solid=False)

    # --- 7. Interior Furnishings (all on FLOOR_TOP_Z = +4.0 cm) ---
    # Stablemaster reception desk (east-center, facing NW toward doorway)
    place_on('OakTable', 120.0, 20.0, FLOOR_TOP_Z, yaw=-12.0, solid=True)
    # Desk top props (table height = 76.7 cm -> Z = 80.7 cm)
    desk_z = FLOOR_TOP_Z + 76.7
    place_on('Measure', 152.0, 12.0, desk_z, yaw=22.0, solid=False)
    place_on('ShoeingWork', 88.0, 16.0, desk_z, yaw=-28.0, solid=False)
    # Visitor & desk stools
    place_on('OakStool', 120.0, -48.0, FLOOR_TOP_Z, yaw=14.0, solid=True)
    place_on('OakStool', 195.0, 42.0, FLOOR_TOP_Z, yaw=-65.0, solid=True)
    # Oak display/record shelf against south rear stone wall
    place_on('OakShelf', 110.0, 224.0, FLOOR_TOP_Z, yaw=180.0, solid=True)
    # Shelf small props (lower shelf ~ 44 cm, mid shelf ~ 95 cm)
    place_on('Measure', 75.0, 220.0, FLOOR_TOP_Z + 94.0, yaw=-15.0, solid=False)
    # Interior potted herb placed squarely on cabin wooden floor beside rear oak shelf (no elevated/floating pots)
    place_on('WindowPot', 208.0, 226.0, FLOOR_TOP_Z, yaw=28.0, solid=False)
    # Stablemaster rest bunk tucked cleanly in SW corner
    place_on('TimberBed', -192.0, 138.0, FLOOR_TOP_Z, yaw=0.0, solid=True)
    # Tack / tools joiner's chest against west wall under west window (clear of inward door swing!)
    place_on('Chest', -215.0, -25.0, FLOOR_TOP_Z, yaw=90.0, solid=True)
    place_on('ChestLid', -215.0, -25.0, FLOOR_TOP_Z + 36.5, yaw=90.0, solid=False)
    place_on('Tools', -210.0, -22.0, FLOOR_TOP_Z + 44.0, yaw=76.0, solid=False)
    # Dry feed cask & oat sacks neatly along east wall under east window
    place_on('AleCask', 216.0, -180.0, FLOOR_TOP_Z, yaw=18.0, solid=True)
    place_on('TiedSack', 212.0, -112.0, FLOOR_TOP_Z, yaw=-24.0, solid=True)
    place_on('GrainSack', 208.0, 162.0, FLOOR_TOP_Z, yaw=82.0, solid=True)
    place_on('GrainSack', 206.0, 165.0, FLOOR_TOP_Z + 20.5, yaw=94.0, solid=False)
    # Exterior potted herbs placed squarely on the ground outside front stone foundation plinth & steps
    place_on('WindowPot', -18.0, -362.0, 0.0, yaw=18.0, solid=False)
    place_on('WindowPot', 226.0, -362.0, 0.0, yaw=-24.0, solid=False)
    # 3D Horse Tack Showcase inside cabin: Hero Saddle Stand (south center) & Tack Wall Rack (east stone wall)
    place_on('SaddleStand', -52.0, 192.0, FLOOR_TOP_Z, yaw=-24.0, solid=True)
    put_raw('TackWallRack', 273.0, 138.0, 156.0 + FOUNDATION_LIFT, yaw=90.0, solid=False)

    comps = add_instances(actors, groups, meshes.__getitem__, PREFIX, tags)
    for (role, solid), comp in comps.items():
        if not solid and role in ('Measure', 'ShoeingWork', 'Tools', 'WindowPot', 'Flagstone'):
            comp.set_cast_shadow(False)
            comp.set_cull_distances(9000, 12000)

    door_report = _install_cabin_door(actors, meshes['DoorLeaf'], existing_door)
    lights_report = _install_lights(actors, meshes['Lantern'], wick)
    sign_report = _install_cabin_trade_sign(actors)
    daylight_label = _install_daylight(actors)
    npc_report = _relocate_stablemaster(actors)

    return dict(
        scope='master_house',
        center_cm=[HOUSE_CX, HOUSE_CY, FLOOR_TOP_Z],
        bounds_cm=[HOUSE_CX - 320.0, HOUSE_CY - 320.0, HOUSE_CX + 320.0, HOUSE_CY + 320.0],
        instances={r: len(poses) for (r, _), poses in groups.items()},
        door=door_report,
        lights=lights_report,
        trade_sign=sign_report,
        daylight=daylight_label,
        stablemaster=npc_report,
    )
