"""Dress the expanded closed stable yard, west paddock, and working stalls using existing village assets."""
from collections import Counter, defaultdict
import math
from pathlib import Path
import random
import sys
import unreal as ue

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / 'AbandonedVillage')]
from shop_staff_light import WICK
from stable_actors import ASSEMBLY, ROOT, add_instances, label_stable
from stable_lighting import (
    CHAIN_MESH,
    add_lantern_and_light,
    append_pendant_hardware,
    append_wall_bracket_hardware,
    make_chain_ism,
    make_iron_hardware_ism,
)

TAG = 'VillageStable.GroundDetailR4'
HILLS = '/Game/WorldGeneration/TemperateHills/'
YARD = HILLS + 'VillageWindmill/Yard/Meshes/SM_Mill'
CHIP = HILLS + 'WhiteCliffs/Meshes/Fractures/SM_QuarryChip'
SURFACES = ROOT + '/GroundDetailR4/'

EXTRA_MESHES = {
    'HayA': YARD + 'HayA',
    'HayB': YARD + 'HayB',
    'OakSkid': YARD + 'OakSkid',
    'HayCrib': ROOT + '/Meshes/SM_Stable_HayCrib',
    'HitchRail': ROOT + '/Meshes/SM_Stable_A08',
    'WashBarrel': HILLS + 'VillageCarpenter/InteriorR1/SM_CarpenterWashBarrel',
    'StackedCases': HILLS + 'VillageCarpenter/InteriorR1/SM_CarpenterStackedCases',
    'LogStack': HILLS + 'VillageCarpenter/Props/SM_CarpenterLogStack',
    'Tools': HILLS + 'VillageCarpenter/Props/SM_CarpenterTools',
    'ShoeingWork': HILLS + 'VillageShopRest/SM_SmithShoeingWork',
    'WheelAndCases': HILLS + 'VillageBlacksmith/TradeSign/SM_SmithWheelAndCases',
    'OakStool': HILLS + 'VillageBlacksmith/ArtPassR2/Meshes/SM_VillageOakStool',
    'AleCask': '/Game/WorldGeneration/VillageTavern/Service/SM_TavernAleCask',
    'GrainSack': HILLS + 'VillageBakery/Grain/SM_BakeryGrainSack',
    'HazelA': HILLS + 'ForestSpecies20261110/Meshes/SM_Hazel_A',
    'HazelB': HILLS + 'ForestSpecies20261110/Meshes/SM_Hazel_B',
    'HazelC': HILLS + 'ForestSpecies20261110/Meshes/SM_Hazel_C',
    'ShrubA': '/Game/UnrealNormandy/StaticMeshes/SM_PlantTypeA_01A',
    'ShrubB': '/Game/UnrealNormandy/StaticMeshes/SM_PlantTypeB_01A',
    'ShrubC': '/Game/UnrealNormandy/StaticMeshes/SM_PlantTypeC_01A',
    'GrassLow': HILLS + 'WetForest/ScannedGrass/SM_SoftWildGrassLow',
    'GrassTuft': HILLS + 'WetForest/ScannedGrass/SM_SoftWildGrassTuft',
    'Twig1': HILLS + 'WetForest/Underfoot/SM_ForestTwig01',
    'Twig2': HILLS + 'WetForest/Underfoot/SM_ForestTwig02',
    'TimberBlock': HILLS + 'VillageCarpenter/Props/SM_CarpenterBlock',
    'AbandonedTimber': HILLS + 'VillageBlacksmith/ArtPassR2/Meshes/SM_VillageAbandonedTimber',
    'Lantern': '/Game/UnrealNormandy/StaticMeshes/SM_Props_Lantern_02A',
    'SaddleStand': ROOT + '/PropsR43/SM_Stable_SaddleStand',
    'TackWallRack': ROOT + '/PropsR43/SM_Stable_TackWallRack',
    'JumpRail': ROOT + '/PropsR43/SM_Stable_JumpRail',
    'HayWagon': ROOT + '/PropsR43/SM_Stable_HayWagon',
    # Exterior RoadUpgrade-R48 Road-Body PCG meshes (all NoCollision, CastShadow=False, FOLLOW-grounded)
    'RoadSmallRock': '/Game/ForestPathStudy/VillageRegion/RoadUpgrade/Rocks/wjvsbay/wjvsbay_tier_2/StaticMeshes/wjvsbay_tier_2',
    'RoadCrownA': '/Game/ForestPathStudy/VillageRegion/RoadUpgrade/Foliage/rbdoo/rbdoo_tier_2/StaticMeshes/SM_rbdoo_VarA',
    'RoadCrownB': '/Game/ForestPathStudy/VillageRegion/RoadUpgrade/Foliage/rbdoo/rbdoo_tier_2/StaticMeshes/SM_rbdoo_VarB',
    'RoadCrownC': '/Game/ForestPathStudy/VillageRegion/RoadUpgrade/Foliage/rbdoo/rbdoo_tier_2/StaticMeshes/SM_rbdoo_VarC',
    'RoadWeedA': '/Game/ForestPathStudy/VillageRegion/RoadUpgrade/Foliage/qmCkL/qmCkL_tier_2/StaticMeshes/SM_qmCkL_VarA',
    'RoadWeedB': '/Game/ForestPathStudy/VillageRegion/RoadUpgrade/Foliage/qmCkL/qmCkL_tier_2/StaticMeshes/SM_qmCkL_VarB',
    'RoadWeedC': '/Game/ForestPathStudy/VillageRegion/RoadUpgrade/Foliage/qmCkL/qmCkL_tier_2/StaticMeshes/SM_qmCkL_VarC',
    'RoadCloverA': '/Game/ForestPathStudy/VillageRegion/RoadUpgrade/Foliage/rbpof/rbpof_tier_2/StaticMeshes/SM_rbpof_VarA',
    'RoadCloverB': '/Game/ForestPathStudy/VillageRegion/RoadUpgrade/Foliage/rbpof/rbpof_tier_2/StaticMeshes/SM_rbpof_VarB',
    'RoadCloverC': '/Game/ForestPathStudy/VillageRegion/RoadUpgrade/Foliage/rbpof/rbpof_tier_2/StaticMeshes/SM_rbpof_VarC',
    'RoadDryB': '/Game/ForestPathStudy/VillageRegion/RoadUpgrade/Foliage/uddmcgbia/uddmcgbia_tier_2/StaticMeshes/SM_uddmcgbia_VarB',
    'RoadDryC': '/Game/ForestPathStudy/VillageRegion/RoadUpgrade/Foliage/uddmcgbia/uddmcgbia_tier_2/StaticMeshes/SM_uddmcgbia_VarC',
    'RoadWildB': '/Game/ForestPathStudy/VillageRegion/RoadUpgrade/Foliage/vczndjqja/vczndjqja_tier_2/StaticMeshes/SM_vczndjqja_VarB',
    'RoadWildC': '/Game/ForestPathStudy/VillageRegion/RoadUpgrade/Foliage/vczndjqja/vczndjqja_tier_2/StaticMeshes/SM_vczndjqja_VarC',
}

ROAD_PCG_ROLES = {
    'RoadSmallRock',
    'RoadCrownA', 'RoadCrownB', 'RoadCrownC',
    'RoadWeedA', 'RoadWeedB', 'RoadWeedC',
    'RoadCloverA', 'RoadCloverB', 'RoadCloverC',
    'RoadDryB', 'RoadDryC',
    'RoadWildB', 'RoadWildC',
}

# Verified Ecology leaf overrides matching ForestCourtyardShrubs.cpp for Normandy courtyard shrubs (slot 0).
SHRUB_LEAF_OVERRIDES = {
    'ShrubA': HILLS + 'EcologyUpgrade/Materials/MI_Leaf_091d476864b6',
    'ShrubB': HILLS + 'EcologyUpgrade/Materials/MI_Leaf_8eed6424d21a',
    'ShrubC': HILLS + 'EcologyUpgrade/Materials/MI_Leaf_fa3dbcc37a09',
}

TRADE_ROOT = HILLS + 'VillageTradeSigns'
SMITH_SIGN = HILLS + 'VillageBlacksmith/ForgeR2/SM_SmithSign'

# Freestanding yard street lamps removed from stable enclosure per PropsR44 user directive.
YARD_LAMP_POSTS = []


def _install_stable_waypost(actors):
    """Place the roadside wooden guild waypost + MI_StableSign outside the north LeadHorseGate."""
    label = 'Village_TradeWaypost_Stable'
    for a in list(actors.get_all_level_actors()):
        if a.get_actor_label() == label:
            actors.destroy_actor(a)
    wx, wy, wyaw = 4365.0, 1520.0, 90.0  # Local -Y arm points +X east toward the Stable gates!
    frame = ue.Transform(location=(wx, wy, 0.0), rotation=ue.Rotator(yaw=wyaw))
    host = label_stable(actors.spawn_actor_from_class(ue.Actor, ue.Vector(wx, wy, 0.0), ue.Rotator(yaw=wyaw)),
                        label, [ASSEMBLY, TAG, 'VillageShop.HangingSign'])
    subs = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
    data = ue.SubobjectDataBlueprintFunctionLibrary
    parent = subs.k2_gather_subobject_data_for_instance(host)[0]
    if not host.root_component:
        h, err = subs.add_new_subobject(ue.AddNewSubobjectParams(parent_handle=parent, new_class=ue.SceneComponent))
        if not data.get_associated_object(data.get_data(h)):
            raise RuntimeError(str(err))
    host.root_component.set_mobility(ue.ComponentMobility.STATIC)
    host.set_actor_transform(frame, False, True)

    def load_req(p):
        obj = ue.load_asset(p)
        if not obj:
            raise RuntimeError('Missing trade sign asset: ' + p)
        return obj

    def add_comp(path, local_loc=(0, 0, 0), sc=1.0, moving=False, solid=False):
        h, err = subs.add_new_subobject(ue.AddNewSubobjectParams(parent_handle=parent, new_class=ue.StaticMeshComponent))
        mc = data.get_associated_object(data.get_data(h))
        if not mc:
            raise RuntimeError(str(err))
        mc.set_mobility(ue.ComponentMobility.MOVABLE if moving else ue.ComponentMobility.STATIC)
        mc.set_static_mesh(load_req(path))
        mc.set_relative_location(ue.Vector(*local_loc), False, True)
        mc.set_relative_scale3d(ue.Vector(sc, sc, sc))
        mc.set_collision_profile_name('BlockAll' if solid else 'NoCollision')
        if not solid:
            mc.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
        mc.set_editor_property('receives_decals', False)
        return mc

    sc = 0.76
    add_comp(TRADE_ROOT + '/SM_TradeWaypost', (0.0, 0.0, 0.0), 1.0, False, True)
    add_comp(SMITH_SIGN + 'BracketR2', (0.0, -7.0, 266.0), sc, False, False)
    add_comp(SMITH_SIGN + 'LinksR2', (0.0, -7.0, 266.0 - 4.2 * sc), sc, True, False)
    panel = add_comp(SMITH_SIGN + 'BoardR2', (0.0, -7.0, 266.0 - 10.35 * sc), sc, True, False)
    slot = panel.get_material_index('Paint')
    if slot < 0:
        raise RuntimeError('Missing Paint slot on ' + SMITH_SIGN + 'BoardR2')
    panel.set_material(slot, load_req(TRADE_ROOT + '/MI_StableSign'))
    return dict(actor=label, world_cm=[wx, wy, 0.0], yaw_deg=wyaw, material=TRADE_ROOT + '/MI_StableSign')


def _install_yard_lights(actors, lantern_mesh, wick):
    host_label = 'Village_Stable_Dressing_YardLights'
    host = label_stable(actors.spawn_actor_from_class(ue.Actor, ue.Vector()), host_label, [ASSEMBLY, TAG])
    subs = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
    data = ue.SubobjectDataBlueprintFunctionLibrary
    parent = subs.k2_gather_subobject_data_for_instance(host)[0]
    if not host.root_component:
        h, err = subs.add_new_subobject(ue.AddNewSubobjectParams(parent_handle=parent, new_class=ue.SceneComponent))
        if not data.get_associated_object(data.get_data(h)):
            raise RuntimeError(str(err))
    host.root_component.set_mobility(ue.ComponentMobility.STATIC)

    box = lantern_mesh.get_bounding_box()
    z_mid = (box.min.z + box.max.z) * 0.5
    lantern_h = float(box.max.z - box.min.z)

    # Gate piers, barn west gable, PLUS lanterns hung directly onto the forged hooks of both YardLampPosts!
    stations = [
        ('WestGatePier', 950.0, 3669.0, 192.0, 2300.0, 0.85),
        ('LeadGatePier', 4503.0, 1600.0, 192.0, 2300.0, 0.85),
        ('BarnWestGable', 3255.0, 3568.0, 265.0, 2500.0, 0.90),
    ]
    for post_name, px, py, pyaw in YARD_LAMP_POSTS:
        rad = math.radians(pyaw)
        hx = px + 36.0 * math.cos(rad)
        hy = py + 36.0 * math.sin(rad)
        # Hang lantern top bail right on the hook saddle at Z = 232 cm
        hz = 232.0 - lantern_h * 0.86 * 0.48
        stations.append((post_name + '_Lantern', round(hx, 1), round(hy, 1), round(hz, 1), 2600.0, 0.96))

    out = []
    for name, wx, wy, wz, draw_dist, level in stations:
        h_mesh, err = subs.add_new_subobject(ue.AddNewSubobjectParams(parent_handle=parent, new_class=ue.StaticMeshComponent))
        mc = data.get_associated_object(data.get_data(h_mesh))
        if not mc:
            raise RuntimeError(str(err))
        mc.set_mobility(ue.ComponentMobility.STATIC)
        mc.set_static_mesh(lantern_mesh)
        mc.set_relative_location(ue.Vector(wx, wy, wz - z_mid * 0.86), False, True)
        mc.set_relative_scale3d(ue.Vector(0.80, 0.80, 0.86))
        mc.set_material(0, wick)
        mc.set_cast_shadow(False)
        mc.set_collision_profile_name('NoCollision')
        mc.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
        mc.set_editor_property('receives_decals', False)

        h_light, err = subs.add_new_subobject(ue.AddNewSubobjectParams(parent_handle=parent, new_class=ue.PointLightComponent))
        lc = data.get_associated_object(data.get_data(h_light))
        if not lc:
            raise RuntimeError(str(err))
        lc.set_mobility(ue.ComponentMobility.MOVABLE)
        lc.set_relative_location(ue.Vector(wx, wy, wz - 4.0), False, True)
        ue.VillageInteriorLighting.configure(lc, level)
        lc.set_editor_property('max_draw_distance', draw_dist)
        lc.set_cast_shadows(False)
        out.append(dict(name=name, mount='post', world_cm=[wx, wy, wz], max_draw_distance=draw_dist))

    # StableLightsR50: Install forged-iron stall-divider lanterns between every barn stall bay
    # (Stall 1|2 @ X=3740, Stall 2|3 @ X=4180, Stall 3|4 @ X=4620, Stall 4|Fodder @ X=5060):
    #   a) Front oak pilaster wall-bracket lanterns (Y_wall=3535.5, hang Y=3499.0, Z=202..235 cm)
    #      clear of roof eave (Y=3520.2, Z>=282.5), A01_Bent corbel (Z>=270), A03 walls, stall doors & apron props.
    #   b) Interior tie-beam pendants directly above each A05 stall partition (X=divider-8.0 centered under
    #      measured A01_Bent tie-beam [-23.3,+3.3], Y=3812.0, soffit Z=271.2, lantern Z=216..250 cm,
    #      +51 cm clear above A05 top 165 cm and +114 cm clear above HayCrib top 102 cm).
    chain_mesh = ue.load_asset(CHAIN_MESH)
    if not chain_mesh:
        raise RuntimeError('Missing chain mesh: ' + CHAIN_MESH)
    chain_box = chain_mesh.get_bounding_box()
    iron_poses, chain_poses = [], []

    stall_dividers = (
        ('StallDivider12', 3740.0),
        ('StallDivider23', 4180.0),
        ('StallDivider34', 4620.0),
        ('StallDivider45', 5060.0),
    )
    for div_name, div_x in stall_dividers:
        # Front courtyard oak pilaster bracket lantern (facing -Y into yard/forecourt)
        f_wall_y, f_reach, f_arm_z = 3535.5, 36.5, 250.0
        f_bottom_z, f_h = 202.0, 33.0
        fx, fy = append_wall_bracket_hardware(
            iron_poses, chain_poses, chain_box,
            div_x, f_wall_y, 0.0, -1.0, f_arm_z, f_reach, f_bottom_z + f_h, brace_drop_cm=16.0,
        )
        f_info = add_lantern_and_light(
            subs, data, parent, lantern_mesh, wick,
            fx, fy, f_bottom_z, f_h, yaw_deg=0.0,
            level=0.68, draw_dist=2400.0, attenuation_radius=620.0,
        )
        out.append(dict(
            name=div_name + '_Front',
            mount='front_pilaster_bracket',
            world_cm=[round(fx, 1), round(fy, 1), f_info['light_z']],
            lantern_z_cm=[f_info['bottom_z'], f_info['top_z']],
            max_draw_distance=2400.0,
            attenuation_radius=620.0,
        ))

        # Interior stall-divider overhead tie-beam pendant (centered on beam soffit above A05 partition)
        i_x, i_y, i_soffit_z = div_x - 8.0, 3812.0, 271.2
        i_bottom_z, i_h = 216.0, 34.0
        append_pendant_hardware(
            iron_poses, chain_poses, chain_box,
            i_x, i_y, i_soffit_z, i_bottom_z + i_h, yaw_deg=90.0,
        )
        i_info = add_lantern_and_light(
            subs, data, parent, lantern_mesh, wick,
            i_x, i_y, i_bottom_z, i_h, yaw_deg=90.0,
            level=0.56, draw_dist=2200.0, attenuation_radius=520.0,
        )
        out.append(dict(
            name=div_name + '_Interior',
            mount='tie_beam_pendant',
            world_cm=[round(i_x, 1), round(i_y, 1), i_info['light_z']],
            lantern_z_cm=[i_info['bottom_z'], i_info['top_z']],
            soffit_z_cm=i_soffit_z,
            max_draw_distance=2200.0,
            attenuation_radius=520.0,
        ))

    iron_ism = make_iron_hardware_ism(subs, data, parent, cull_distance=2600.0)
    iron_ism.add_instances(iron_poses, False, False, False)
    chain_ism = make_chain_ism(subs, data, parent, cull_distance=2600.0)
    chain_ism.add_instances(chain_poses, False, False, False)
    return out


def install_ground_detail(actors):
    owned = [a for a in actors.get_all_level_actors() if ASSEMBLY in map(str, a.tags)]

    def part(label, cls):
        found = [a.get_component_by_class(cls) for a in owned if a.get_actor_label() == 'Village_Stable_' + label]
        if len(found) != 1 or not found[0]:
            raise RuntimeError('Cannot locate stable ' + label)
        return found[0]

    floor = part('PackedFloor', ue.InstancedStaticMeshComponent)
    traffic = part('Traffic', ue.DecalComponent)
    before = dict(
        floor=floor.get_material(0).get_path_name(),
        yard=traffic.get_decal_material().get_path_name(),
        floor_receives_decals=floor.get_editor_property('receives_decals'),
    )

    def load(path):
        asset = ue.load_asset(path)
        if not asset:
            raise RuntimeError('Missing stable detail ' + path)
        return asset

    meshes = {k: load(YARD + k) for k in (
        'EarthShoulder', 'FieldstoneA', 'FieldstoneB', 'FieldstoneC',
        'Chaff', 'Fork', 'Barrow', 'Measure', 'Grain', 'TiedSack'
    )}
    for i in range(1, 7):
        meshes['Chip' + str(i)] = load(CHIP + f'{i:02}')
    for k, path in EXTRA_MESHES.items():
        meshes[k] = load(path)
    bounds = {k: v.get_bounding_box() for k, v in meshes.items()}
    floor_mat = load(SURFACES + 'M_StableStallFloor')
    yard_mat = load(SURFACES + 'M_StableYardSoil')
    west_paddock_mat = ue.load_asset(SURFACES + 'M_StableWestPaddockSoil')
    wick = load(WICK)

    for a in owned:
        if TAG in map(str, a.tags):
            actors.destroy_actor(a)

    # Preserve Traffic decal material binding (ForestVillage swaps to VillageStableEntryWear),
    # and widen vertical projection depth (45 cm) so ForecourtR45 heightfield relief never clips the decal.
    floor.modify()
    floor.set_material(0, floor_mat)
    traffic.modify()
    traffic.get_owner().modify()
    traffic.get_owner().set_actor_location(ue.Vector(4500, 2500, 1), False, True)
    traffic.set_editor_property('decal_size', ue.Vector(45, 2200, 1800))
    traffic.set_decal_material(yard_mat)

    # Dedicated west-paddock soil decal covering X: 8..31 m, Y: 32..47 m (center 1950, 3950).
    west_decal_path = None
    if west_paddock_mat:
        wp = label_stable(
            actors.spawn_actor_from_class(ue.DecalActor, ue.Vector(1950, 3950, 1), ue.Rotator(pitch=-90)),
            'Village_Stable_WestPaddock_Soil',
            [ASSEMBLY, TAG],
        )
        dc = wp.get_component_by_class(ue.DecalComponent)
        dc.set_editor_property('decal_size', ue.Vector(45, 750, 1150))
        dc.set_decal_material(west_paddock_mat)
        dc.set_fade_screen_size(.001)
        west_decal_path = west_paddock_mat.get_path_name()

    placed = defaultdict(list)
    zones = Counter()
    rng = random.Random(61748)

    def fit(zone, role, x, y, z, w, d, h, yaw, solid=False):
        b = bounds[role]
        base = ue.Vector((b.min.x + b.max.x) / 2, (b.min.y + b.max.y) / 2, b.min.z)
        frame = ue.Transform(
            location=(x, y, z),
            rotation=ue.Rotator(yaw=yaw),
            scale=ue.Vector(w, d, h) / (b.max - b.min),
        )
        placed[role, solid].append(ue.MathLibrary.compose_transforms(ue.Transform(location=-base), frame))
        zones[zone] += 1

    def place_native(zone, role, x, y, z, yaw=0.0, scale=1.0, solid=True):
        b = bounds[role]
        base = ue.Vector((b.min.x + b.max.x) / 2, (b.min.y + b.max.y) / 2, b.min.z)
        frame = ue.Transform(
            location=(x, y, z),
            rotation=ue.Rotator(yaw=yaw),
            scale=(scale, scale, scale),
        )
        placed[role, solid].append(ue.MathLibrary.compose_transforms(ue.Transform(location=-base), frame))
        zones[zone] += 1

    def place_shrub(zone, role, x, y, target_h_cm, yaw=0.0, sink_cm=3.5):
        """Seat a shrub cleanly to target height in cm (slight root sink prevents slope gaps)."""
        b = bounds[role]
        span_z = max(1.0, float(b.max.z - b.min.z))
        sc = float(target_h_cm) / span_z
        place_native(zone, role, x, y, -sink_cm, yaw=yaw, scale=sc, solid=False)

    # --- 1. Stone & gravel pockets along fence margins (clear of all gates, turning circle, and riding track) ---
    pockets = [
        ('bakery edge', 4268, 2040, 45, 65), ('bakery edge', 4410, 2260, 36, 41),
        ('bakery edge', 4545, 2580, 26, 75), ('bakery edge', 4530, 2940, 28, 70),
        ('bakery edge', 4160, 3230, 72, 24), ('bakery edge', 3780, 3270, 70, 22),
        ('north divider', 4885, 1650, 58, 22), ('forecourt ne', 5665, 1740, 42, 48),
        ('cart verge', 5754, 2000, 19, 69), ('cart verge', 5750, 2360, 24, 68),
        ('cart verge', 5756, 2800, 18, 61), ('cart verge', 5742, 3180, 26, 72),
        ('back fence', 3650, 4565, 90, 16), ('back fence', 4888, 4565, 78, 16),
        ('feed gable', 5754, 3730, 19, 49),
        # Expanded west & south paddock fence edges
        ('west fence', 995, 4280, 22, 75), ('west fence', 1005, 3460, 22, 55),
        ('south paddock', 1550, 4570, 95, 18), ('south paddock', 2840, 4570, 85, 18),
        ('north paddock', 1420, 3365, 85, 18), ('north paddock', 2080, 3355, 75, 18),
    ]
    for j, (zone, cx, cy, rx, ry) in enumerate(pockets):
        used = []
        for i in range(14):
            angle = rng.uniform(0, math.tau)
            offset = math.sqrt(rng.random())
            px, py = cx + rx * offset * math.cos(angle), cy + ry * offset * math.sin(angle)
            w = rng.uniform(12, 20) if not used else rng.uniform(3, 10)
            if any(math.hypot(px - ux, py - uy) < (s + w) * .55 for ux, uy, s in used):
                continue
            role = ('Fieldstone' + 'ABC'[j % 3]) if not used else 'Chip' + str(rng.randint(1, 6))
            used.append((px, py, w))
            h = w * rng.uniform(.30, .49)
            fit(zone, role, px, py, -h * rng.uniform(.35, .59), w, w * rng.uniform(.61, .87), h, rng.uniform(0, 180))

    # Grounded fence footing earth shoulders (forecourt perimeter + outer paddock)
    for x, y, w, d, h, angle in [
        (5752, 1810, 145, 48, 7, 89),
        (5754, 2290, 168, 52, 7, 88),
        (5752, 3190, 165, 48, 7, 91),
        (4538, 2610, 172, 46, 6, 89),
        (4525, 2930, 155, 44, 6, 94),
        (4230, 3195, 165, 44, 6, -14),
        (4882, 1642, 150, 42, 5, 1),
        (4395, 4560, 198, 49, 6, 2),
        (995, 4340, 175, 46, 6, 89),
        (1650, 4568, 210, 48, 6, 1),
        (2760, 4568, 190, 46, 6, -2),
        (1950, 3345, 185, 44, 5, 3),
    ]:
        fit('fence footing', 'EarthShoulder', x, y, -2.7, w, d, h, angle)

    # --- 2. Natural shrubs, wild grass & twigs framing forecourt & paddock fence margins (all FOLLOW-prefixed) ---
    for sx, sy, s_scale, syaw in [
        (1035, 4535, 0.25, 24.0),
        (1040, 3395, 0.22, -48.0),
        (1320, 4545, 0.23, 112.0),
        (2870, 4550, 0.24, -18.0),
        (5710, 4535, 0.25, 67.0),
    ]:
        place_native('fence flora', 'HazelB', sx, sy, -2.0, yaw=syaw, scale=s_scale, solid=False)

    # Forecourt perimeter layered shrubs (Normandy courtyard ShrubA/B/C + HazelA/B/C)
    # Strictly tucked along fence corners & posts, clear of all inward gate swings and riding lanes!
    forecourt_shrubs = [
        # NE corner & East fence line (left side when entering via Wagon/Lead gates)
        ('ShrubB', 5665, 1675, 108, 28),
        ('HazelB', 5735, 1745, 128, -42),
        ('ShrubA', 5728, 1815, 86, 114),
        ('ShrubC', 5742, 2065, 96, -15),
        ('ShrubA', 5742, 2235, 88, 64),
        ('HazelA', 5746, 2425, 105, -82),
        ('ShrubB', 5745, 2580, 92, 145),
        ('HazelC', 5742, 2945, 122, 36),
        ('ShrubC', 5735, 3070, 102, -64),
        ('ShrubA', 5740, 3155, 84, 18),
        # North mid-fence divider between LeadHorseGate (4754) & WagonGate (5008)
        ('ShrubA', 4882, 1648, 72, 12),
        ('ShrubC', 4820, 1642, 62, -48),
        # NW Bakery-wall alcove (right foreground when entering)
        ('ShrubB', 4445, 1775, 102, -32),
        ('HazelC', 4350, 1848, 116, 75),
        ('ShrubA', 4215, 1930, 96, 128),
        ('HazelB', 4210, 2120, 118, -54),
        ('ShrubC', 4330, 2295, 92, 44),
        ('ShrubA', 4458, 2375, 86, -18),
        # Mid-West fence line hugging X=4503 (keeps X=4625 lead-horse lane wide open)
        ('ShrubB', 4540, 2490, 102, 52),
        ('HazelA', 4545, 2565, 92, -110),
        ('ShrubC', 4542, 2725, 108, 22),
        ('ShrubA', 4540, 2808, 82, 134),
        ('HazelB', 4512, 2975, 112, -28),
        ('ShrubB', 4455, 3092, 96, 86),
        # SW forecourt bend toward barn (north of Y=3300 riding track)
        ('ShrubA', 4338, 3158, 88, -62),
        ('HazelC', 4148, 3212, 106, 42),
        ('ShrubC', 3928, 3255, 94, 118),
        ('ShrubB', 3742, 3260, 104, -36),
    ]
    for srole, sx, sy, sh, syaw in forecourt_shrubs:
        place_shrub('forecourt flora', srole, sx, sy, sh, yaw=syaw, sink_cm=3.5)

    grass_spots = [
        # Outer paddock & rear fence (existing)
        (1025, 4460), (1055, 4555), (1160, 4565), (1285, 4565), (1440, 4565),
        (1890, 4565), (2060, 4565), (2420, 4565), (2750, 4565), (2940, 4560),
        (1030, 3440), (1085, 3365), (1245, 3360), (1540, 3355), (2020, 3345),
        (2740, 3295), (5735, 4470), (5740, 4390), (5740, 3500), (5740, 1730),
        (1310, 4415), (1995, 4425),
        # Forecourt east fence rim (Y=1660..3460)
        (5600, 1665), (5705, 1795), (5725, 1920), (5725, 2060), (5730, 2195),
        (5725, 2320), (5735, 2450), (5738, 2595), (5742, 2745), (5740, 2890),
        (5730, 3030), (5725, 3165), (5720, 3315), (5725, 3440),
        # Forecourt north divider & NW bakery alcove
        (4815, 1650), (4890, 1655), (4955, 1648),
        (4445, 1790), (4325, 1875), (4215, 1985), (4220, 2140), (4345, 2295),
        # Forecourt west fence & SW bend
        (4485, 2395), (4542, 2515), (4548, 2655), (4545, 2795), (4535, 2935),
        (4475, 3075), (4355, 3155), (4195, 3215), (4025, 3255), (3840, 3268),
        # Barn north timber pilasters (between doors, never blocking stalls)
        (3740, 3510), (4180, 3510), (4620, 3510), (5060, 3510),
    ]
    for idx, (gx, gy) in enumerate(grass_spots):
        for sub in range(2):
            ox = gx + rng.uniform(-34, 34)
            oy = gy + rng.uniform(-24, 24)
            role = 'GrassTuft' if (idx + sub) % 2 == 0 else 'GrassLow'
            sc = rng.uniform(0.75, 1.22)
            place_native('fence flora', role, ox, oy, -1.5, yaw=rng.uniform(0, 360), scale=sc, solid=False)

    # Weathered forest twigs near forecourt shrubs, log stacks & fence footing (auto-follows relief)
    twig_spots = [
        (5635, 1720), (5690, 1835), (5665, 2095), (5615, 2235), (5660, 2435),
        (5695, 2610), (5685, 2995), (5665, 3145), (5640, 3385), (4875, 1675),
        (4415, 1815), (4270, 1945), (4245, 2150), (4385, 2310), (4565, 2480),
        (4575, 2675), (4565, 2860), (4490, 3045), (4315, 3180), (4115, 3240),
        (3890, 3275), (3710, 3285), (4215, 3495), (5035, 3485),
    ]
    for tidx, (tx, ty) in enumerate(twig_spots):
        trole = 'Twig1' if tidx % 2 == 0 else 'Twig2'
        place_native('forecourt flora', trole, tx + rng.uniform(-16, 16), ty + rng.uniform(-16, 16),
                     -0.6, yaw=rng.uniform(0, 360), scale=rng.uniform(0.72, 1.15), solid=False)

    # --- 3. Working Barn Stall Chaff, Fodder Bay, and East Service Barrow (preserved R4 detail) ---
    for i, cx in enumerate((3520, 3960, 4400, 4840)):
        for dx, cy, w, d in [(-125, 3760, 105, 49), (118, 3882, 87, 44), (-106, 3910, 59, 26)]:
            fit('stall ' + str(i + 1), 'Chaff', cx + dx + rng.uniform(-6, 6), cy + rng.uniform(-8, 8),
                .83, w * rng.uniform(.86, 1.1), d, rng.uniform(1.5, 3.5), rng.uniform(-40, 48))
    for px, py, w, d in [(5362, 3764, 74, 43), (5377, 3943, 59, 37), (5401, 4056, 48, 28)]:
        fit('fodder store', 'Chaff', px, py, .85, w, d, 2.5, rng.uniform(-55, 55))
    fit('fodder store', 'TiedSack', 5480, 4010, .65, 35, 32, 45, 12, True)
    fit('fodder store', 'Measure', 5448, 4065, .69, 29, 23, 20, -17, True)
    fit('fodder store', 'Grain', 5410, 4038, .80, 24, 16, 1.7, -24)
    placed['Fork', False].append(ue.Transform(location=(5343, 3875, 1.25), rotation=ue.Rotator(pitch=-18)))
    zones['fodder store'] += 1
    fit('service strip', 'Barrow', 5646, 3820, -.35, 163, 65, 47, 91, True)
    fit('service strip', 'Chaff', 5641, 3734, .35, 44, 31, 2.2, 32)

    # --- 4. Farrier & Horse-Care Corner (near Watering Trough 2975,4080 & Barn West Gable) ---
    place_native('farrier corner', 'WashBarrel', 3095, 4230, 0.0, yaw=18.0, solid=True)
    place_native('farrier corner', 'WashBarrel', 2885, 4215, 0.0, yaw=-42.0, solid=True)
    place_native('farrier corner', 'OakSkid', 3115, 4355, 0.0, yaw=12.0, solid=False)
    place_native('farrier corner', 'ShoeingWork', 3095, 4350, 11.5, yaw=28.0, solid=False)
    place_native('farrier corner', 'Tools', 3138, 4360, 11.5, yaw=-22.0, solid=False)
    place_native('farrier corner', 'OakStool', 3045, 4345, 0.0, yaw=40.0, solid=True)
    place_native('farrier corner', 'AleCask', 3245, 4370, 0.0, yaw=8.0, solid=True)

    # --- 5. North Paddock Feeding Station & Extra Hitching Rail (along north fence Y~3350..3440) ---
    place_native('north paddock', 'HitchRail', 1760, 3425, 0.0, yaw=0.0, solid=True)
    place_native('north paddock', 'HayCrib', 2340, 3385, 0.0, yaw=0.0, solid=True)
    fit('north paddock', 'HayA', 2340, 3385, 52.0, 96, 34, 30, 0.0, False)
    for dx, dy, cw, cd in [(-45, 38, 86, 44), (48, 42, 74, 38), (5, 55, 62, 32)]:
        fit('north paddock', 'Chaff', 2340 + dx, 3385 + dy, 0.4, cw, cd, 2.4, rng.uniform(-40, 40), False)
    # Spare hay bale stack on oak skids + leaned pitchfork east of crib
    fit('north paddock', 'OakSkid', 2585, 3415, 0.0, 210, 112, 12, 2.0, True)
    fit('north paddock', 'HayA', 2535, 3415, 12.0, 102, 58, 48, 3.0, True)
    fit('north paddock', 'HayB', 2635, 3415, 12.0, 100, 56, 46, -2.0, True)
    fit('north paddock', 'HayB', 2585, 3415, 58.0, 98, 56, 45, 86.0, True)
    placed['Fork', False].append(ue.Transform(location=(2490, 3458, 1.0), rotation=ue.Rotator(pitch=-18, yaw=35)))
    zones['north paddock'] += 1
    fit('north paddock', 'Chaff', 2580, 3485, 0.4, 98, 54, 2.5, 14.0, False)

    # --- 6. South Paddock Storage Edge (along rear fence Y~4520, leaving center riding paddock wide open) ---
    place_native('south paddock', 'WheelAndCases', 2580, 4520, 0.0, yaw=176.0, solid=True)
    place_native('south paddock', 'LogStack', 2210, 4535, 0.0, yaw=3.0, solid=True)
    fit('south paddock', 'TiedSack', 3405, 4535, 0.0, 44, 36, 56, 22.0, True)
    place_native('south paddock', 'GrainSack', 3465, 4540, 0.0, yaw=-15.0, solid=True)

    # --- 7. Stablemaster Cabin Exterior Accents (Rainwater barrel, west supply cluster, NW barrow; broken trench bench retired) ---
    # Rainwater barrel by cabin NE eave
    place_native('cabin apron', 'WashBarrel', 2005, 3868, 0.0, yaw=12.0, solid=True)
    # West-side dry supplies (clear of WestPaddockGate inward swing X:950..1180, Y:3669..3920)
    place_native('cabin apron', 'StackedCases', 1278, 4235, 0.0, yaw=92.0, solid=True)
    place_native('cabin apron', 'AleCask', 1278, 4318, 0.0, yaw=20.0, solid=True)
    place_native('cabin apron', 'GrainSack', 1278, 4135, 0.0, yaw=84.0, solid=True)
    place_native('cabin apron', 'GrainSack', 1278, 4135, 20.5, yaw=95.0, solid=False)
    # Second yard barrow parked cleanly in NW paddock corner (north of West Gate)
    fit('cabin apron', 'Barrow', 1145, 3465, -0.3, 163, 65, 47, 28.0, True)
    fit('cabin apron', 'Chaff', 1150, 3465, 16.0, 62, 42, 10.0, 28.0, False)

    # --- 8. R44 Hero Equestrian Props: Saddle Stand, Barn Tack Rack, Playable Jump Rail & Hay Wagon ---
    # Outdoor saddle stand on cabin shaded east apron beside rainwater barrel
    place_native('hero tack', 'SaddleStand', 2055, 4045, 0.0, yaw=-16.0, solid=True)
    # Outdoor wall tack rack mounted flush on Barn West Gable (X=3269, centered between both A08 hitching rails)
    placed['TackWallRack', False].append(ue.Transform(location=(3269.0, 3938.0, 184.0), rotation=ue.Rotator(yaw=90.0)))
    zones['hero tack'] += 1
    # Playable equestrian jump hurdle centered in expanded west riding arena (clear gallop run-up E/W, height 98 cm)
    place_native('riding arena', 'JumpRail', 2420, 3980, 0.0, yaw=86.0, solid=True)
    # Four-wheel loaded hay wagon parked cleanly along eastern side of the 9 m forecourt turning yard
    place_native('forecourt wagon', 'HayWagon', 5430, 2760, 0.0, yaw=-112.0, solid=True)

    # --- 9. ForecourtR45 Perimeter Clutter & Working Stable Vignettes (strictly outside gates & turning lanes) ---
    # 9a. NE Corner Dry-Goods & Tool Staging (east of WagonGate pier X=5492, clear of inward gate leaf)
    place_native('forecourt east', 'WashBarrel', 5665, 1875, 0.0, yaw=22.0, solid=True)
    place_native('forecourt east', 'StackedCases', 5690, 1975, 0.0, yaw=-6.0, solid=True)
    place_native('forecourt east', 'GrainSack', 5618, 1938, 0.0, yaw=34.0, solid=True)
    place_native('forecourt east', 'GrainSack', 5622, 1942, 20.5, yaw=52.0, solid=False)
    placed['Fork', False].append(ue.Transform(location=(5732, 2032, 1.0), rotation=ue.Rotator(pitch=-16, yaw=188)))
    zones['forecourt east'] += 1
    fit('forecourt east', 'Chaff', 5638, 1982, 0.4, 84, 46, 2.2, 24.0, False)

    # 9b. Mid-East Fence Timber, Spare Hay Skid & Wheelwright Corner (leading directly into HayWagon)
    place_native('forecourt east', 'LogStack', 5695, 2140, 0.0, yaw=88.0, solid=True)
    place_native('forecourt east', 'AleCask', 5638, 2215, 0.0, yaw=16.0, solid=True)
    place_native('forecourt east', 'TimberBlock', 5608, 2278, 0.0, yaw=24.0, solid=True)
    fit('forecourt east', 'OakSkid', 5685, 2350, 0.0, 196, 108, 12, 89.0, True)
    fit('forecourt east', 'HayA', 5685, 2312, 12.0, 96, 56, 46, 92.0, True)
    fit('forecourt east', 'HayB', 5685, 2392, 12.0, 94, 54, 44, 86.0, True)
    fit('forecourt east', 'Chaff', 5608, 2355, 0.4, 78, 44, 2.4, -18.0, False)
    place_native('forecourt east', 'WheelAndCases', 5672, 2482, 0.0, yaw=-84.0, solid=True)

    # 9c. SE Forecourt Corner (south of HayWagon toward Fodder Bay entrance)
    place_native('forecourt east', 'WashBarrel', 5685, 3235, 0.0, yaw=-32.0, solid=True)
    fit('forecourt east', 'TiedSack', 5630, 3282, 0.0, 42, 34, 52, 18.0, True)
    place_native('forecourt east', 'GrainSack', 5692, 3335, 0.0, yaw=76.0, solid=True)
    fit('forecourt east', 'Measure', 5645, 3338, 0.0, 28, 22, 20, -24.0, False)
    place_native('forecourt east', 'OakStool', 5605, 3378, 0.0, yaw=32.0, solid=True)
    place_native('forecourt east', 'AbandonedTimber', 5702, 3428, 0.0, yaw=86.0, solid=True)
    fit('forecourt east', 'Chaff', 5645, 3312, 0.4, 72, 40, 2.2, 12.0, False)

    # 9d. NW Bakery-Wall Alcove (right foreground upon entering gates, well off LeadHorse lane X~4625)
    place_native('forecourt west', 'LogStack', 4255, 2005, 0.0, yaw=86.0, solid=True)
    fit('forecourt west', 'Barrow', 4325, 2088, -0.3, 163, 65, 47, 34.0, True)
    fit('forecourt west', 'Chaff', 4332, 2088, 16.0, 62, 42, 10.0, 34.0, False)
    fit('forecourt west', 'Chaff', 4355, 2130, 0.4, 68, 38, 2.2, -28.0, False)
    place_native('forecourt west', 'WashBarrel', 4265, 2192, 0.0, yaw=14.0, solid=True)
    place_native('forecourt west', 'AleCask', 4342, 2218, 0.0, yaw=-26.0, solid=True)
    fit('forecourt west', 'TiedSack', 4398, 2245, 0.0, 42, 35, 52, -14.0, True)
    place_native('forecourt west', 'OakStool', 4385, 1995, 0.0, yaw=-40.0, solid=True)

    # 9e. SW Forecourt Bend along north fence margin (Y=3155..3285, leaves Y=3310..3520 riding lane open)
    place_native('forecourt west', 'WashBarrel', 4405, 3155, 0.0, yaw=28.0, solid=True)
    place_native('forecourt west', 'AleCask', 4272, 3212, 0.0, yaw=-18.0, solid=True)
    fit('forecourt west', 'TiedSack', 4215, 3232, 0.0, 40, 34, 50, 24.0, True)
    fit('forecourt west', 'OakSkid', 4045, 3260, 0.0, 140, 82, 11, 4.0, True)
    fit('forecourt west', 'HayB', 4045, 3260, 11.0, 96, 54, 44, 6.0, True)
    fit('forecourt west', 'Chaff', 4045, 3308, 0.4, 78, 42, 2.2, -12.0, False)

    # 9f. Barn North Pilaster Accents (strictly beside posts between stall doors X=3740/4180/4620/5060)
    place_native('barn apron', 'OakStool', 4185, 3500, 0.0, yaw=18.0, solid=True)
    place_native('barn apron', 'WashBarrel', 5065, 3495, 0.0, yaw=-22.0, solid=True)
    fit('barn apron', 'TiedSack', 5015, 3500, 0.0, 40, 34, 50, 15.0, True)
    place_native('barn apron', 'GrainSack', 4970, 3505, 0.0, yaw=-12.0, solid=True)
    placed['Fork', False].append(ue.Transform(location=(5092, 3510, 1.0), rotation=ue.Rotator(pitch=-16, yaw=155)))
    zones['barn apron'] += 1
    for cx, cy in ((3740, 3495), (4620, 3495), (5040, 3475)):
        fit('barn apron', 'Chaff', cx, cy, 0.4, 64, 36, 2.0, rng.uniform(-35, 35), False)

    # --- 10. StableRoadPCGR51: Exterior RoadUpgrade-R48 Road-Body PCG Ground Cover ---
    # Covers BOTH open horse activity areas (Entrance Forecourt & West Riding Paddock) using the exact
    # R48 RoadLandscape non-periodic Neyman-Scott cluster palette (pebbles, quarry chips, low crushed
    # crown grass, flat road weeds, clover patches & verge dry/wild tufts). Zero solid collision;
    # every mesh is registered in ForestVillageRelief FOLLOW prefixes so it conforms to curved heightfield!
    pcg_rng = random.Random(514807)

    # Exclusion boxes for buildings, wagons, jump rail & watering trough so no ground-cover grass pokes inside solid footprints
    pcg_exclusions = (
        (1310, 3760, 2010, 4460),  # Stablemaster cabin + plinth + steps
        (3250, 3530, 5540, 4400),  # Stable barn & stalls
        (5260, 2550, 5600, 2970),  # HayWagon
        (2860, 4000, 3260, 4420),  # Watering trough & farrier corner
        (2330, 3780, 2510, 4180),  # JumpRail hurdle
        (2260, 3330, 2710, 3500),  # North paddock HayCrib + hay stack
    )

    def pcg_clear(px, py):
        for x0, y0, x1, y1 in pcg_exclusions:
            if x0 <= px <= x1 and y0 <= py <= y1:
                return False
        return True

    def place_road_pcg(zone, role, px, py, scale, sink_cm):
        if not pcg_clear(px, py):
            return
        place_native(zone, role, px, py, -sink_cm, yaw=pcg_rng.uniform(0.0, 360.0), scale=scale, solid=False)

    # 10a. Entrance Forecourt Horse Activity Area (X: 4540..5720, Y: 1680..3470 + SW track X: 3360..4540, Y: 3280..3480)
    # Cluster centers distributed organically across the forecourt, denser near rims & sparse across active hoof lanes
    forecourt_pebble_centers = [
        (4660, 1980), (4920, 1940), (5280, 1980), (5540, 2020),
        (4620, 2240), (4840, 2280), (5120, 2260), (5460, 2220),
        (4680, 2540), (4960, 2580), (5180, 2560), (4640, 2860),
        (4900, 2890), (5140, 2920), (4680, 3160), (4960, 3190),
        (5260, 3180), (5520, 3160), (4480, 3320), (4220, 3360),
        (3920, 3390), (3620, 3380), (4820, 3410), (5200, 3420),
        (4380, 2060), (4460, 2320), (5620, 2640), (5560, 3040),
    ]
    for cx, cy in forecourt_pebble_centers:
        for _ in range(pcg_rng.randint(4, 8)):
            ang = pcg_rng.uniform(0.0, math.tau)
            rad = min(pcg_rng.expovariate(1.0 / 68.0), 175.0)
            px = max(3340.0, min(5720.0, cx + math.cos(ang) * rad))
            py = max(1720.0, min(3470.0, cy + math.sin(ang) * rad))
            if pcg_rng.random() < 0.56:
                place_road_pcg('road pcg forecourt', 'RoadSmallRock', px, py, pcg_rng.uniform(0.68, 1.38), sink_cm=1.9)
            else:
                chip = 'Chip' + str(pcg_rng.randint(1, 6))
                place_road_pcg('road pcg forecourt', chip, px, py, pcg_rng.uniform(0.32, 0.72), sink_cm=1.6)

    # Low crushed crown grass, road weeds & clover clusters across the Entrance Forecourt (R48 Zone 1 & 2!)
    forecourt_foliage_centers = [
        # Sparse natural tread islands in open horse roaming area (keep hoof lanes readable)
        (4670, 2120, False), (5080, 2160, False), (4740, 2480, False),
        (5060, 2680, False), (4760, 2960, False), (5120, 3020, False),
        (4880, 3260, False), (5280, 3280, False), (4160, 3340, False),
        (3760, 3370, False), (4520, 3350, False), (4960, 2380, False),
        # Richer verge collars along perimeter fences, gate shoulders & wagon flanks
        (4565, 1860, True), (4880, 1690, True), (5580, 1790, True),
        (5670, 2120, True), (5660, 2460, True), (5640, 3080, True),
        (5560, 3380, True), (4570, 2580, True), (4560, 2880, True),
        (4380, 3180, True), (3980, 3280, True), (3560, 3300, True),
        (4340, 1920, True), (4420, 2240, True),
    ]
    for cx, cy, is_verge in forecourt_foliage_centers:
        n_items = pcg_rng.randint(5, 8) if is_verge else pcg_rng.randint(2, 5)
        for _ in range(n_items):
            ang = pcg_rng.uniform(0.0, math.tau)
            rad = min(pcg_rng.expovariate(1.0 / (58.0 if is_verge else 72.0)), 155.0)
            px = max(3340.0, min(5725.0, cx + math.cos(ang) * rad))
            py = max(1670.0, min(3470.0, cy + math.sin(ang) * rad))
            r = pcg_rng.random()
            if is_verge:
                if r < 0.24:
                    role = 'RoadDry' + pcg_rng.choice(('B', 'C'))
                    place_road_pcg('road pcg forecourt', role, px, py, pcg_rng.uniform(0.55, 0.90), sink_cm=2.2)
                elif r < 0.48:
                    role = 'RoadCrown' + pcg_rng.choice(('A', 'B', 'C'))
                    place_road_pcg('road pcg forecourt', role, px, py, pcg_rng.uniform(0.42, 0.68), sink_cm=2.4)
                elif r < 0.66:
                    role = 'RoadWeed' + pcg_rng.choice(('A', 'B', 'C'))
                    place_road_pcg('road pcg forecourt', role, px, py, pcg_rng.uniform(0.52, 0.86), sink_cm=1.5)
                elif r < 0.84:
                    role = 'RoadClover' + pcg_rng.choice(('A', 'B', 'C'))
                    place_road_pcg('road pcg forecourt', role, px, py, pcg_rng.uniform(0.32, 0.54), sink_cm=1.8)
                else:
                    role = 'RoadWild' + pcg_rng.choice(('B', 'C'))
                    place_road_pcg('road pcg forecourt', role, px, py, pcg_rng.uniform(0.38, 0.62), sink_cm=2.8)
            else:
                # Open riding floor: strictly ultra-low weeds, clover & short crushed crown grass
                if r < 0.42:
                    role = 'RoadWeed' + pcg_rng.choice(('A', 'B', 'C'))
                    place_road_pcg('road pcg forecourt', role, px, py, pcg_rng.uniform(0.44, 0.74), sink_cm=1.5)
                elif r < 0.72:
                    role = 'RoadClover' + pcg_rng.choice(('A', 'B', 'C'))
                    place_road_pcg('road pcg forecourt', role, px, py, pcg_rng.uniform(0.28, 0.46), sink_cm=1.8)
                else:
                    role = 'RoadCrown' + pcg_rng.choice(('A', 'B', 'C'))
                    place_road_pcg('road pcg forecourt', role, px, py, pcg_rng.uniform(0.32, 0.50), sink_cm=2.4)

    # 10b. West Horse Riding Paddock (X: 1020..3220, Y: 3380..4560 — open riding arena around JumpRail & cabin!)
    paddock_pebble_centers = [
        (1180, 3560), (1460, 3520), (1840, 3540), (2180, 3620),
        (2640, 3680), (2980, 3660), (2180, 3980), (2720, 3960),
        (2140, 4340), (2540, 4380), (2880, 4440), (1160, 4360),
        (1680, 4520), (3140, 3780), (2940, 3480), (1380, 3680),
    ]
    for cx, cy in paddock_pebble_centers:
        for _ in range(pcg_rng.randint(4, 7)):
            ang = pcg_rng.uniform(0.0, math.tau)
            rad = min(pcg_rng.expovariate(1.0 / 68.0), 170.0)
            px = max(1010.0, min(3220.0, cx + math.cos(ang) * rad))
            py = max(3370.0, min(4565.0, cy + math.sin(ang) * rad))
            if pcg_rng.random() < 0.58:
                place_road_pcg('road pcg paddock', 'RoadSmallRock', px, py, pcg_rng.uniform(0.68, 1.35), sink_cm=1.9)
            else:
                chip = 'Chip' + str(pcg_rng.randint(1, 6))
                place_road_pcg('road pcg paddock', chip, px, py, pcg_rng.uniform(0.32, 0.70), sink_cm=1.6)

    paddock_foliage_centers = [
        # Open paddock tread islands
        (2160, 3760, False), (2680, 3760, False), (2220, 4180, False),
        (2680, 4220, False), (2960, 3740, False), (1540, 3560, False),
        (1920, 3580, False), (2520, 3600, False), (2420, 4340, False),
        # Paddock perimeter verges
        (1060, 3520, True), (1050, 4120, True), (1080, 4480, True),
        (1420, 4520, True), (2060, 4520, True), (2780, 4520, True),
        (1340, 3390, True), (1980, 3390, True), (2880, 3420, True),
    ]
    for cx, cy, is_verge in paddock_foliage_centers:
        n_items = pcg_rng.randint(4, 7) if is_verge else pcg_rng.randint(2, 5)
        for _ in range(n_items):
            ang = pcg_rng.uniform(0.0, math.tau)
            rad = min(pcg_rng.expovariate(1.0 / (56.0 if is_verge else 70.0)), 150.0)
            px = max(1010.0, min(3220.0, cx + math.cos(ang) * rad))
            py = max(3370.0, min(4565.0, cy + math.sin(ang) * rad))
            r = pcg_rng.random()
            if is_verge:
                if r < 0.28:
                    role = 'RoadDry' + pcg_rng.choice(('B', 'C'))
                    place_road_pcg('road pcg paddock', role, px, py, pcg_rng.uniform(0.55, 0.88), sink_cm=2.2)
                elif r < 0.54:
                    role = 'RoadCrown' + pcg_rng.choice(('A', 'B', 'C'))
                    place_road_pcg('road pcg paddock', role, px, py, pcg_rng.uniform(0.42, 0.66), sink_cm=2.4)
                elif r < 0.78:
                    role = 'RoadClover' + pcg_rng.choice(('A', 'B', 'C'))
                    place_road_pcg('road pcg paddock', role, px, py, pcg_rng.uniform(0.32, 0.52), sink_cm=1.8)
                else:
                    role = 'RoadWild' + pcg_rng.choice(('B', 'C'))
                    place_road_pcg('road pcg paddock', role, px, py, pcg_rng.uniform(0.38, 0.60), sink_cm=2.8)
            else:
                if r < 0.42:
                    role = 'RoadWeed' + pcg_rng.choice(('A', 'B', 'C'))
                    place_road_pcg('road pcg paddock', role, px, py, pcg_rng.uniform(0.44, 0.72), sink_cm=1.5)
                elif r < 0.74:
                    role = 'RoadClover' + pcg_rng.choice(('A', 'B', 'C'))
                    place_road_pcg('road pcg paddock', role, px, py, pcg_rng.uniform(0.28, 0.46), sink_cm=1.8)
                else:
                    role = 'RoadCrown' + pcg_rng.choice(('A', 'B', 'C'))
                    place_road_pcg('road pcg paddock', role, px, py, pcg_rng.uniform(0.32, 0.50), sink_cm=2.4)

    comps = add_instances(actors, placed, meshes.__getitem__, 'Village_Stable_Dressing_', [ASSEMBLY, TAG])
    for (role, solid), comp in comps.items():
        if role in SHRUB_LEAF_OVERRIDES:
            comp.set_material(0, load(SHRUB_LEAF_OVERRIDES[role]))
            comp.set_cast_shadow(False)
            comp.set_cull_distances(12000, 16000)
        elif role in ROAD_PCG_ROLES:
            comp.set_cast_shadow(False)
            comp.set_editor_property('receives_decals', False)
            comp.set_editor_property('affect_distance_field_lighting', False)
            comp.set_editor_property('affect_dynamic_indirect_lighting', False)
            for rt_prop in ('visible_in_ray_tracing', 'b_visible_in_ray_tracing'):
                try:
                    comp.set_editor_property(rt_prop, False)
                    break
                except Exception:
                    pass
            comp.set_cull_distances(2550, 3400)
            if role != 'RoadSmallRock':
                try:
                    comp.set_editor_property('world_position_offset_disable_distance', 2200)
                except Exception:
                    pass
        elif role.startswith('Chip') or role in ('Chaff', 'Grain', 'GrassLow', 'GrassTuft', 'Twig1', 'Twig2'):
            comp.set_cast_shadow(False)
            comp.set_cull_distances(14000, 18000)
        elif role in ('HazelA', 'HazelB', 'HazelC'):
            comp.set_cast_shadow(True)
            comp.set_cull_distances(16000, 21000)

    yard_lights = _install_yard_lights(actors, meshes['Lantern'], wick)
    waypost_report = _install_stable_waypost(actors)

    return dict(
        scope='ground_detail',
        previous_bindings=before,
        yard=traffic.get_decal_material().get_path_name(),
        west_paddock_decal=west_decal_path,
        floor=floor.get_material(0).get_path_name(),
        yard_lights=yard_lights,
        stable_waypost=waypost_report,
        instances={role: c.get_instance_count() for (role, _), c in comps.items()},
        zones=dict(zones),
    )
