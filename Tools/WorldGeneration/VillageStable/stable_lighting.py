"""Reusable forged-iron ceiling pendant and wall-bracket lantern builders for EastGateStable."""
import math
import unreal as ue

LANTERN_MESH = '/Game/UnrealNormandy/StaticMeshes/SM_Props_Lantern_02A'
CHAIN_MESH = '/Game/UndergroundTunnel/Meshes/Props/SM_ChainLink01a'
CYLINDER_MESH = '/Engine/BasicShapes/Cylinder'
IRON_MAT = '/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterIron'


def _require(path):
    obj = ue.load_asset(path)
    if not obj:
        raise RuntimeError('Missing stable lighting asset: ' + path)
    return obj


def _add_subobject(subs, data, parent, cls):
    h, err = subs.add_new_subobject(ue.AddNewSubobjectParams(parent_handle=parent, new_class=cls))
    obj = data.get_associated_object(data.get_data(h))
    if not obj:
        raise RuntimeError(str(err))
    return obj


def _rod_transform(p0, p1, diameter_cm):
    a = ue.Vector(*p0)
    b = ue.Vector(*p1)
    delta = b - a
    length = float(delta.length())
    if length < 1e-4:
        raise RuntimeError(f'Zero-length iron rod from {p0} to {p1}')
    axis = delta / length
    rot = ue.MathLibrary.make_rot_from_z(axis)
    mid = (a + b) * 0.5
    return ue.Transform(location=mid, rotation=rot, scale=ue.Vector(diameter_cm * 0.01, diameter_cm * 0.01, length * 0.01))


def make_iron_hardware_ism(subs, data, parent, cull_distance=2600.0):
    """Create a single NoCollision InstancedStaticMeshComponent for forged-iron plates/rods/struts."""
    ism = _add_subobject(subs, data, parent, ue.InstancedStaticMeshComponent)
    ism.set_mobility(ue.ComponentMobility.STATIC)
    ism.set_static_mesh(_require(CYLINDER_MESH))
    ism.set_material(0, _require(IRON_MAT))
    ism.set_collision_profile_name('NoCollision')
    ism.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
    ism.set_editor_property('receives_decals', False)
    ism.set_cast_shadow(False)
    ism.set_cull_distances(0, int(cull_distance))
    return ism


def make_chain_ism(subs, data, parent, cull_distance=2600.0):
    """Create a single NoCollision InstancedStaticMeshComponent for forged-iron hanging chain links."""
    ism = _add_subobject(subs, data, parent, ue.InstancedStaticMeshComponent)
    ism.set_mobility(ue.ComponentMobility.STATIC)
    ism.set_static_mesh(_require(CHAIN_MESH))
    ism.set_material(0, _require(IRON_MAT))
    ism.set_collision_profile_name('NoCollision')
    ism.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
    ism.set_editor_property('receives_decals', False)
    ism.set_cast_shadow(False)
    ism.set_cull_distances(0, int(cull_distance))
    return ism


def add_lantern_and_light(
    subs,
    data,
    parent,
    lantern_mesh,
    wick,
    x,
    y,
    bottom_z,
    height_cm,
    yaw_deg,
    level,
    draw_dist,
    attenuation_radius=None,
    cull_dist=2600.0,
):
    """Place a NoCollision SM_Props_Lantern_02A (exact bottom_z..bottom_z+height_cm) + warm PointLight."""
    box = lantern_mesh.get_bounding_box()
    cx = (float(box.min.x) + float(box.max.x)) * 0.5
    cy = (float(box.min.y) + float(box.max.y)) * 0.5
    scale = float(height_cm) / max(1.0, float(box.max.z - box.min.z))
    pivot = ue.Transform(location=ue.Vector(-cx, -cy, -float(box.min.z)))
    local = ue.Transform(
        location=ue.Vector(x, y, bottom_z),
        rotation=ue.Rotator(yaw=yaw_deg),
        scale=ue.Vector(scale, scale, scale),
    )
    tf = ue.MathLibrary.compose_transforms(pivot, local)

    mc = _add_subobject(subs, data, parent, ue.StaticMeshComponent)
    mc.set_mobility(ue.ComponentMobility.STATIC)
    mc.set_static_mesh(lantern_mesh)
    mc.set_relative_transform(tf, False, True)
    mc.set_material(0, wick)
    mc.set_cast_shadow(False)
    mc.set_collision_profile_name('NoCollision')
    mc.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
    mc.set_editor_property('receives_decals', False)
    mc.set_editor_property('ld_max_draw_distance', float(cull_dist))

    light_z = bottom_z + 0.46 * height_cm
    lc = _add_subobject(subs, data, parent, ue.PointLightComponent)
    lc.set_mobility(ue.ComponentMobility.MOVABLE)
    lc.set_relative_location(ue.Vector(x, y, light_z), False, True)
    ue.VillageInteriorLighting.configure(lc, float(level))
    if attenuation_radius is not None:
        lc.set_editor_property('attenuation_radius', float(attenuation_radius))
    lc.set_editor_property('max_draw_distance', float(draw_dist))
    lc.set_editor_property('max_distance_fade_range', 450.0)
    lc.set_cast_shadows(False)
    return dict(bottom_z=round(bottom_z, 2), top_z=round(bottom_z + height_cm, 2), light_z=round(light_z, 2), scale=round(scale, 4))


def append_pendant_hardware(iron_poses, chain_poses, chain_box, x, y, soffit_z, crown_z, yaw_deg=0.0):
    """Build shop_pendants.py-style riveted ceiling plate, plumb drop rod, cross pins & forged chain link."""
    rad = math.radians(yaw_deg)
    ca, sa = math.cos(rad), math.sin(rad)

    # Riveted iron ceiling plate flush against timber beam soffit
    iron_poses.append(ue.Transform(
        location=ue.Vector(x, y, soffit_z + 0.1),
        rotation=ue.Rotator(yaw=yaw_deg),
        scale=ue.Vector(0.10, 0.066, 0.02),
    ))
    for d in (-3.6, 3.6):
        iron_poses.append(ue.Transform(
            location=ue.Vector(x + d * ca, y + d * sa, soffit_z - 0.85),
            rotation=ue.Rotator(yaw=yaw_deg),
            scale=ue.Vector(0.013, 0.013, 0.012),
        ))

    # Plumb drop rod from soffit down to chain cross-pin (10 cm above lantern crown)
    pin_z = crown_z + 10.0
    if soffit_z > pin_z + 1.0:
        iron_poses.append(_rod_transform((x, y, pin_z - 0.5), (x, y, soffit_z + 0.5), 1.55))
    for pz in (pin_z, crown_z - 0.4):
        iron_poses.append(ue.Transform(
            location=ue.Vector(x, y, pz),
            rotation=ue.Rotator(pitch=90.0, yaw=yaw_deg),
            scale=ue.Vector(0.011, 0.011, 0.044),
        ))

    # Forged chain link bridging crown_z..pin_z cleanly
    span = max(11.0, (pin_z - crown_z) + 2.8)
    c_len = max(1.0, float(chain_box.max.x - chain_box.min.x))
    sc = span / c_len
    c_mid = ue.Vector(
        (float(chain_box.min.x) + float(chain_box.max.x)) * 0.5,
        (float(chain_box.min.y) + float(chain_box.max.y)) * 0.5,
        (float(chain_box.min.z) + float(chain_box.max.z)) * 0.5,
    )
    pivot = ue.Transform(location=-c_mid)
    target = ue.Transform(
        location=ue.Vector(x, y, (crown_z + pin_z) * 0.5 - 0.2),
        rotation=ue.Rotator(pitch=90.0, yaw=yaw_deg + 20.0),
        scale=ue.Vector(sc, sc, sc),
    )
    chain_poses.append(ue.MathLibrary.compose_transforms(pivot, target))


def append_wall_bracket_hardware(
    iron_poses,
    chain_poses,
    chain_box,
    wall_x,
    wall_y,
    out_dx,
    out_dy,
    arm_z,
    reach_cm,
    crown_z,
    brace_drop_cm=16.0,
):
    """Build AVillageShopChainLamp-style riveted wall plate, horizontal arm, diagonal strut & 2-link chain."""
    # Wall plate embedded 2 cm into timber/plaster and standing 2 cm proud
    p_back = (wall_x - out_dx * 2.0, wall_y - out_dy * 2.0, arm_z)
    p_front = (wall_x + out_dx * 2.5, wall_y + out_dy * 2.5, arm_z)
    iron_poses.append(_rod_transform(p_back, p_front, 11.0))
    for dz in (-3.8, 3.8):
        iron_poses.append(_rod_transform(
            (wall_x + out_dx * 1.5, wall_y + out_dy * 1.5, arm_z + dz),
            (wall_x + out_dx * 3.6, wall_y + out_dy * 3.6, arm_z + dz),
            1.6,
        ))

    # Horizontal cantilever arm projecting out past the lantern hang point
    arm_tip = reach_cm + 2.0
    iron_poses.append(_rod_transform(
        (wall_x - out_dx * 1.5, wall_y - out_dy * 1.5, arm_z),
        (wall_x + out_dx * arm_tip, wall_y + out_dy * arm_tip, arm_z),
        2.9,
    ))

    # Diagonal support strut below cantilever arm
    strut_reach = max(14.0, reach_cm - 7.5)
    iron_poses.append(_rod_transform(
        (wall_x - out_dx * 1.0, wall_y - out_dy * 1.0, arm_z - brace_drop_cm),
        (wall_x + out_dx * strut_reach, wall_y + out_dy * strut_reach, arm_z),
        2.3,
    ))

    # Two interlaced forged chain links connecting arm_z down to lantern crown bail
    hx = wall_x + out_dx * reach_cm
    hy = wall_y + out_dy * reach_cm
    drop = max(8.0, arm_z - crown_z)
    link_len = max(8.5, drop * 0.68)
    c_len = max(1.0, float(chain_box.max.x - chain_box.min.x))
    sc = link_len / c_len
    c_mid = ue.Vector(
        (float(chain_box.min.x) + float(chain_box.max.x)) * 0.5,
        (float(chain_box.min.y) + float(chain_box.max.y)) * 0.5,
        (float(chain_box.min.z) + float(chain_box.max.z)) * 0.5,
    )
    pivot = ue.Transform(location=-c_mid)
    for idx, z_mid in enumerate((arm_z - link_len * 0.36, crown_z + link_len * 0.36)):
        target = ue.Transform(
            location=ue.Vector(hx, hy, z_mid),
            rotation=ue.Rotator(pitch=90.0, yaw=idx * 90.0),
            scale=ue.Vector(sc, sc, sc),
        )
        chain_poses.append(ue.MathLibrary.compose_transforms(pivot, target))
    return hx, hy
