"""The apothecary's oak floor and return stair, in plot-local centimetres."""
import unreal as u

from author_shop import pose, require
from LoftR3.design import ASSET_ROOT, HALF, LOFT_Z, OPENING, STAIR


# Plot 03 retains its original Normandy shell. Its side wall axes are at
# -346.24 and +349.76 cm. Fit the oak deck into the masonry on both sides.
PLAN_SCALE = .90
CENTER_X = 1.76
GUARD = '/Game/WorldGeneration/TemperateHills/VillageBlacksmith/DetailR6/Meshes/SM_SmithLoft_Guardrails_R6'
OAK = '/Game/UnrealNormandy/StaticMeshes/SM_HW_Plank_01A'
IRON = '/Game/Props/CastingStation20260926/RealismV5/MI_DarkForgedIron'


def add_loft(house, add):
    frame = pose(house, 0, 0)
    fitted = u.MathLibrary.compose_transforms(
        u.Transform(location=[CENTER_X, 0, 0], scale=[PLAN_SCALE, PLAN_SCALE, 1]), frame)
    for role in ('UpperFloor', 'Stair'):
        add('Common', ASSET_ROOT + '/Meshes/SM_SmithLoft_' + role, fitted)
    add('Common', GUARD, fitted, extra=('Traversal.GuardrailDrop',))

    # The deck already has joists and stairwell trimmers. Their ends bear on
    # two longitudinal ledgers pocketed into the side walls. The west ledger
    # sits entirely under the narrow strip of boards outside the stairwell.
    bounds = require(OAK).get_bounding_box()
    centre = (bounds.max + bounds.min) * .5
    span = bounds.max - bounds.min

    def timber(state, x, y, z, length, width, height, profile='BlockAll'):
        placement = u.Transform(location=[x, y, z], rotation=u.Rotator(yaw=90),
                                scale=[length / span.x, width / span.y, height / span.z])
        local = u.MathLibrary.compose_transforms(u.Transform(location=-centre), placement)
        add(state, OAK, u.MathLibrary.compose_transforms(local, frame), profile=profile)

    for wall_x in (-344., 347.5):
        timber('Common', wall_x, 0, 327, 704, 22, 22)

    # A face-fixed repair plate over the east bearing is visible from the
    # counter. It stays below the joists and clear of the stairs and lights.
    timber('Repaired', 334.5, 116, 327, 80, 5, 14, profile='NoCollision')
    for y in (86, 116, 146):
        nail = u.Transform(location=[331.8, y, 327], rotation=u.Rotator(pitch=90),
                           scale=[.025, .025, .018])
        add('Repaired', '/Engine/BasicShapes/Cylinder',
            u.MathLibrary.compose_transforms(nail, frame), (IRON,), profile='NoCollision')

    xmin, xmax, ymin, ymax = OPENING
    return {
        'floor_top_cm': LOFT_Z,
        'deck_size_cm': [2 * HALF * PLAN_SCALE] * 2,
        'stairwell_xyxy_cm': [CENTER_X + xmin * PLAN_SCALE, ymin * PLAN_SCALE,
                              CENTER_X + xmax * PLAN_SCALE, ymax * PLAN_SCALE],
        'stair_entry_cm': [CENTER_X + STAIR['first_x'] * PLAN_SCALE,
                           STAIR['start_y'] * PLAN_SCALE, 0],
        'stair_exit_cm': [CENTER_X + STAIR['second_x'] * PLAN_SCALE,
                          STAIR['start_y'] * PLAN_SCALE, LOFT_Z],
        'flight_width_cm': STAIR['width'] * PLAN_SCALE,
        'rise_cm': STAIR['rise'],
        'going_cm': STAIR['tread'] * PLAN_SCALE,
        'risers_per_flight': STAIR['steps_per_flight'],
        'floor_stair_and_guard_state': 'Common',
    }
