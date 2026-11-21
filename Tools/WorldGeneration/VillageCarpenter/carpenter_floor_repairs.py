"""Shop-specific scanned floor planks and bearing details, in the existing floor frame."""
DECK = '/Game/WorldGeneration/TemperateHills/VillageCarpenter/Structure/SM_CarpenterDeck'
JOINTS = (-60, 60, 0, -60, 60, -60, 60, 0, -60, 60)
INFILL_ROW = 6


def add_ground_deck(parts, part_transform, board):
    for p in parts:
        if 'SM_WoodenFloor_' not in p['mesh']:
            continue
        east = p['pos'][0] > 0
        part_transform(p, DECK + ('East' if east else 'West'))
        if east:
            # The original tile retains its flat continuous walking collision.
            # Both pieces of infill are visual meshes seated over the same joists.
            infill = dict(p, profile='NoCollision')
            part_transform(infill, DECK + 'WornPlank', 'Ruined')
            part_transform(infill, DECK + 'SplicedPlank', 'Repaired')

    # Hidden oak splines sit just above the yard soil, behind the worn board ends.
    # The three rows of butt joints fall on these sleepers or the central sill.
    for x in (-78.53, 1.96, 82.46):
        board('Common', (x,-402,-5.7), (x,402,-5.7), 14, 5.0, 0, profile='NoCollision')
    board('Common', (-400,0,-6.1), (404,0,-6.1), 11, 5.2, 1, profile='NoCollision')

    # The west shoe laps the top of the 25 cm post and the original tie end.
    # At the east seat, a projecting oak corbel is buried in the solid side wall.
    board('Common', (-401,300,335), (-363,300,335), 23, 25, 1)
    board('Common', (-397,300,317), (-348,300,317), 28, 11, 0)
    board('Common', (361,300,335), (402,300,335), 23, 25, 1)
    board('Common', (344,300,315), (405,300,315), 29, 14, 0)
    board('Common', (399,300,282), (351,300,314), 17, 15, 1)
