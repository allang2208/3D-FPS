"""09 south longhouse. The origin is the centre of the public threshold, +Y inside."""
from pathlib import Path
import sys

import unreal as ue

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gunshop_shell_geometry import WALLS

PACK = '/Game/WorldGeneration/TemperateHills/VillageGunshop/Architecture/SM_Gunshop_'
CASEMENT = '/Game/WorldGeneration/TemperateHills/VillageBakery/Architecture/SM_Bakery_'
SMITH = '/Game/WorldGeneration/TemperateHills/VillageBlacksmith/WindowR7/Meshes/SM_SmithLoft_'
PARTS = ('Envelope', 'StoneApron', 'Timber', 'Roof', 'Floors', 'Stair', 'StreetJoinery')


def build_shell(place):
    for part in PARTS:
        if part == 'Floors':
            from shop_house_modules import gunshop_modules, place_modules
            place_modules(place, gunshop_modules())
            continue
        path = PACK + part
        if part == 'StreetJoinery':
            from trade_sign_layout import JOINERY
            path = JOINERY
        mesh = ue.load_asset(path)
        if not mesh:
            raise RuntimeError('Missing fitted gunshop architecture ' + path)
        bounds = mesh.get_bounding_box()
        centre = (bounds.min + bounds.max) * .5
        span = bounds.max - bounds.min
        place(part, path, (centre.x, centre.y, bounds.min.z), (span.x, span.y, span.z),
              solid=part != 'StoneApron')


def window_fittings():
    for axis, line, _, _, openings in WALLS:
        for lo, hi, sill, head in openings:
            if sill == 0:
                continue
            c, z = (lo + hi) * .5, (sill + head) * .5
            outside = -1 if line <= 0 else 1
            centre = (c, line + 25 * outside, z) if axis == 'X' else (line + 25 * outside, c, z)
            yaw = 90 * outside if axis == 'X' else (180 if outside < 0 else 0)
            width = (hi - lo - 1.8) / 148.
            scale = (width, width, (head - sill - 2.4) / 162.)
            yield centre, yaw, scale, axis == 'X' and line == 0 and sill < 340


def install_windows(actors, site, current, require):
    tag = 'VillageGunshop.Window'
    existing = {a.get_actor_label(): a for a in current if tag in map(str, a.tags)}
    keep = ue.AttachmentRule.KEEP_WORLD
    count = 0
    for index, (centre, yaw, scale, storefront) in enumerate(window_fittings(), 1):
        label = 'Village_09_Gunshop_Window_%02d' % index
        local = ue.Transform(location=centre, rotation=ue.Rotator(yaw=yaw), scale=scale)
        world = ue.MathLibrary.compose_transforms(local, site.get_actor_transform())
        window = existing.pop(label, None)
        if not window:
            window = actors.spawn_actor_from_class(ue.ColdSteelWindow, world.translation, world.rotation.rotator())
            window.set_actor_label(label)
        window.modify()
        window.tags = [tag]
        window.attach_to_actor(site, 'None', keep, keep, keep, False)
        window.set_actor_transform(world, False, True)
        window.set_editor_property('use_authored_hinges', True)
        window.set_editor_property('authored_left_hinge', ue.Vector(0, -74, 0))
        window.set_editor_property('authored_right_hinge', ue.Vector(0, 74, 0))
        window.set_editor_property('fixed_swing_direction', 1)
        window.set_editor_property('open_angle_degrees', 99 if storefront else 96)
        window.set_editor_property('open_seconds', .85)
        meshes = {c.get_name(): c for c in window.get_components_by_class(ue.StaticMeshComponent)}
        for component, path in (
                ('WindowFrame', CASEMENT + 'WindowPintles'),
                ('WindowLeafLeft', SMITH + 'WindowLeft_R7b' if storefront else CASEMENT + 'CasementLeft'),
                ('WindowLeafRight', SMITH + 'WindowRight_R7b' if storefront else CASEMENT + 'CasementRight')):
            meshes[component].modify()
            meshes[component].set_static_mesh(require(path))
            meshes[component].set_editor_property('receives_decals', False)
        window.call_method('RefreshAuthoredGeometry')
        window.set_actor_hidden_in_game(True)
        window.set_actor_enable_collision(False)
        count += 1
    for retired in existing.values():
        actors.destroy_actor(retired)
    return count
