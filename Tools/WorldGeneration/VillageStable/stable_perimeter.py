"""Expanded and fully closed post-centre perimeter setting out for the stable (village-local cm)."""
import math
from collections import defaultdict

import unreal as ue

from stable_actors import ASSEMBLY, add_door, add_instances, load_stable_mesh

CLOSURE = 'VillageStable.FenceClosure'
PREFIX = 'Village_Stable_Perimeter_'


def perimeter_chains():
    """Return closed fence chains and gateposts in village-local centimetres."""
    horse_w, horse_e = (4503, 1600), (4754, 1600)
    wagon_w, wagon_e = (5008, 1600), (5492, 1600)  # Existing full-size piers owned by install_stable.
    front_e = (5793, 1600)
    rear_e = (5793, 4620)
    rear_w = (950, 4620)
    west_gate_s = (950, 3920)
    west_gate_n = (950, 3669)  # 251 cm post-to-post = 221 cm clear leaf opening (matches LeadHorseGate).
    north_w = (950, 3320)

    # North-west paddock fence clears Windmill 05 haystack, sorting table, unloading ruts, and rear lane,
    # then joins the existing mill-grove and bakery-wall boundary seamlessly up to horse_w.
    north_and_bakery = [
        west_gate_n,
        north_w,
        (2250, 3300),
        (2808, 3240),
        (3670, 3228),
        (4040, 3198),
        (4440, 3088),
        (4503, 2888),
        (4503, 2400),
        (4153, 2110),
        (4153, 1949),
        (4503, 1744),
        horse_w,
    ]
    east_rear_west = [wagon_e, front_e, rear_e, rear_w, west_gate_s]
    north_mid = [horse_e, wagon_w]
    chains = [north_and_bakery, north_mid, east_rear_west]
    gateposts = {horse_w, horse_e, west_gate_n, west_gate_s}
    existing_piers = {wagon_w, wagon_e}
    return chains, gateposts, existing_piers


def install_stable_perimeter(actors):
    meshes = {key: load_stable_mesh(key) for key in
              ('A06', 'A07', 'FenceRails', 'GatePier', 'HingePintles')}
    lead_gate = None
    west_gate = None
    lead_label = PREFIX + 'LeadHorseGate'
    west_label = PREFIX + 'WestPaddockGate'

    for actor in actors.get_all_level_actors():
        tags = set(map(str, actor.tags))
        label = actor.get_actor_label()
        if ASSEMBLY in tags and CLOSURE in tags and isinstance(actor, ue.ColdSteelDoor):
            if label == lead_label:
                lead_gate = actor
                continue
            if label == west_label:
                west_gate = actor
                continue
        legacy = label in ('Village_Stable_A06', 'Village_Stable_FenceRails')
        if ASSEMBLY in tags and (CLOSURE in tags or legacy):
            actors.destroy_actor(actor)

    groups = defaultdict(list)
    tags = [ASSEMBLY, CLOSURE]

    def put(role, x, y, z=0, yaw=0, scale=(1, 1, 1), solid=True):
        groups[role, solid].append(ue.Transform(location=(x, y, z), rotation=ue.Rotator(yaw=yaw), scale=scale))

    def post(point, gate=False):
        put('GatePier', *point, scale=(24 / 31, 1, 1) if gate else (.75, .70, .79))

    def panel(role, a, b, native_length):
        dx, dy = b[0] - a[0], b[1] - a[1]
        put(role, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, yaw=math.degrees(math.atan2(dy, dx)),
            scale=(math.hypot(dx, dy) / native_length, 1, 1))

    def run(a, b):
        bays = max(1, round(math.dist(a, b) / 225))
        points = [(a[0] + (b[0] - a[0]) * i / bays, a[1] + (b[1] - a[1]) * i / bays) for i in range(bays + 1)]
        for i in range(bays):
            if i % 2 and i < bays - 1:
                panel('A06', points[i], points[i + 1], 214)
            else:
                panel('FenceRails', points[i], points[i + 1], 240)
        if bays % 2 == 0:
            post(points[-2])

    chains, gateposts, existing_piers = perimeter_chains()
    joints = dict.fromkeys(p for chain in chains for p in chain)
    for point in joints:
        if point not in existing_piers:
            post(point, gate=point in gateposts)
    for chain in chains:
        for a, b in zip(chain, chain[1:]):
            run(a, b)

    # North lead-horse gate (swings inward +Y into forecourt).
    add_door(actors, lead_label, 'A07', meshes['A07'], put, 4629.5, 1617.0, 4.5, 90.0, False, tags, actor=lead_gate)
    # West paddock gate (swings inward +X into expanded west paddock).
    add_door(actors, west_label, 'A07', meshes['A07'], put, 967.0, 3794.5, 4.5, 0.0, False, tags, actor=west_gate)

    add_instances(actors, groups, meshes.__getitem__, PREFIX, tags)
    total_length_m = round(sum(math.dist(a, b) for c in chains for a, b in zip(c, c[1:])) / 100.0, 2)
    return dict(
        scope='perimeter',
        closed_enclosure=True,
        instances={r: len(poses) for (r, _), poses in groups.items()},
        doors=['LeadHorseGate', 'WestPaddockGate'],
        fixed_runs=sum(len(c) - 1 for c in chains),
        fence_length_m=total_length_m,
        enclosure_bounds_cm=[950, 1600, 5793, 4620],
        horse_open_clear_cm=221,
        west_gate_clear_cm=221,
    )
