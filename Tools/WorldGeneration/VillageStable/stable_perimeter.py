"""Post-centre setting out for the stable, in village-local centimetres."""
import math
from collections import defaultdict

import unreal as ue

from stable_actors import ASSEMBLY, add_door, add_instances, load_stable_mesh

CLOSURE = 'VillageStable.FenceClosure'
PREFIX = 'Village_Stable_Perimeter_'


def install_stable_perimeter(actors):
    meshes = {key: load_stable_mesh(key) for key in
              ('A06', 'A07', 'FenceRails', 'GatePier', 'HingePintles')}
    lead_gate = None
    gate_label = PREFIX+'LeadHorseGate'
    for actor in actors.get_all_level_actors():
        tags = set(map(str, actor.tags))
        label = actor.get_actor_label()
        if ASSEMBLY in tags and CLOSURE in tags and label == gate_label and isinstance(actor,ue.ColdSteelDoor):
            lead_gate = actor
            continue
        legacy = label in ('Village_Stable_A06', 'Village_Stable_FenceRails')
        if ASSEMBLY in tags and (CLOSURE in tags or legacy):
            actors.destroy_actor(actor)

    groups = defaultdict(list)
    tags = [ASSEMBLY, CLOSURE]

    def put(role, x, y, z=0, yaw=0, scale=(1,1,1), solid=True):
        groups[role, solid].append(ue.Transform(location=(x,y,z), rotation=ue.Rotator(yaw=yaw), scale=scale))

    def post(point, gate=False):
        # The cropped rail-end posts and the taller hinge piers use the same oak and iron.
        put('GatePier', *point, scale=(24/31,1,1) if gate else (.75,.70,.79))

    def panel(role, a, b, native_length):
        dx, dy = b[0]-a[0], b[1]-a[1]
        put(role, (a[0]+b[0])/2, (a[1]+b[1])/2, yaw=math.degrees(math.atan2(dy,dx)),
            scale=(math.hypot(dx,dy)/native_length,1,1))

    def run(a, b):
        bays = max(1, round(math.dist(a,b)/225))
        points = [(a[0]+(b[0]-a[0])*i/bays, a[1]+(b[1]-a[1])*i/bays) for i in range(bays+1)]
        # A06 is 240 cm overall, but its two post centres are only 214 cm apart.
        # Each scanned panel supplies both interior posts. Plain rails end inside
        # those posts. Corners and junctions get one independently oriented pier.
        for i in range(bays):
            if i % 2 and i < bays-1:
                panel('A06', points[i], points[i+1], 214)
            else:
                panel('FenceRails', points[i], points[i+1], 240)
        if bays % 2 == 0:
            post(points[-2])

    horse_w, horse_e = (4503,1600), (4754,1600)
    wagon_w, wagon_e = (5008,1600), (5492,1600)  # Existing full-size piers.
    front_e = (5793,1600)
    feed_end = (5793,4320)

    # Clockwise from the horse entrance. Follow the outer face of the bakery's
    # surviving stone at X 4146.8. The public path remains on the masonry side.
    # The second bend follows the mill grove, clear of the grain ruts and trunks.
    bakery_and_grove = [horse_w, (4503,1744), (4153,1949), (4153,2110),
                        (4503,2400), (4503,2888), (4440,3088), (4040,3198),
                        (3670,3228), (2808,3240)]
    # Stop at the grove and the feed gable. Both routes round the stable are open.
    chains = [bakery_and_grove, [feed_end,front_e,wagon_e], [horse_e,wagon_w]]
    gateposts = {horse_w,horse_e}
    joints = dict.fromkeys(p for chain in chains for p in chain)
    for point in joints:
        if point not in (wagon_w,wagon_e):
            post(point, gate=point in gateposts)
    for chain in chains:
        for a,b in zip(chain,chain[1:]):
            run(a,b)

    add_door(actors, gate_label, 'A07', meshes['A07'], put, 4629.5,1617,4.5,90,False,tags,
             actor=lead_gate)
    add_instances(actors, groups, meshes.__getitem__, PREFIX, tags)
    return dict(scope='perimeter', instances={r:len(poses) for (r,_),poses in groups.items()},
                doors=['LeadHorseGate'], fixed_runs=sum(len(c)-1 for c in chains),
                horse_open_clear_cm=221)
