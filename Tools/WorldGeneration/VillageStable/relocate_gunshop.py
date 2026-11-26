"""Relocate plot 09 gunshop rigidly to the southwest artisan yard and clear footprint scatter."""
from collections import defaultdict
import math
import re
import unreal as ue

# New doorway threshold frame in village-local centimetres (+X east, +Y south).
# Faces north (-Y) directly onto the south lane (-35, 23) m, clear of Carpenter 04 & Tavern 02.
GUNSHOP_TARGET_LOC = ue.Vector(-3450.0, 2700.0, 4.0)
GUNSHOP_TARGET_YAW = 0.0
WAYPOST_TARGET_LOC = ue.Vector(-3950.0, 330.0, 0.0)
WAYPOST_TARGET_YAW = 170.0


def _overlaps_box(x, y, radius, ax, ay, bx, by):
    return math.hypot(max(ax - x, 0.0, x - bx), max(ay - y, 0.0, y - by)) <= radius


def clear_scatter_in_boxes(actors, boxes):
    """Remove wild grass/flowers/rubble/stone ISM instances overlapping any (ax, ay, bx, by) box."""
    removed = defaultdict(int)
    for actor in actors.get_all_level_actors():
        label = actor.get_actor_label()
        if not (re.match(r'^Village_\d+_', label) or label == 'Village_Yards_And_Lanes'):
            continue
        for comp in actor.get_components_by_class(ue.InstancedStaticMeshComponent):
            mesh = comp.static_mesh
            if not mesh:
                continue
            mname = mesh.get_name().lower()
            if not any(k in mname for k in (
                'grass', 'planttype', 'flower', 'rubblepile', 'sm_stone_', 'foresttwig', 'softwildgrass'
            )):
                continue
            bounds = mesh.get_bounding_box()
            center = (bounds.min + bounds.max) * 0.5
            for i in reversed(range(comp.get_instance_count())):
                pose = comp.get_instance_transform(i, True)
                p = ue.MathLibrary.transform_location(pose, center)
                radius = min(170.0, max(
                    (bounds.max.x - bounds.min.x) * abs(pose.scale3d.x),
                    (bounds.max.y - bounds.min.y) * abs(pose.scale3d.y)
                ) * 0.5)
                if any(_overlaps_box(p.x, p.y, radius, *b) for b in boxes):
                    comp.modify()
                    if comp.remove_instance(i):
                        removed[mesh.get_name()] += 1
    return dict(removed)


def relocate_gunshop(actors):
    all_actors = list(actors.get_all_level_actors())
    site = next((a for a in all_actors if 'VillageGunshop.Site' in map(str, a.tags)), None)
    if not site:
        raise RuntimeError('Cannot locate Village_09_Gunshop (VillageGunshop.Site)')

    old_tf = site.get_actor_transform()
    new_tf = ue.Transform(location=GUNSHOP_TARGET_LOC, rotation=ue.Rotator(yaw=GUNSHOP_TARGET_YAW))
    inv_old = ue.MathLibrary.invert_transform(old_tf)

    # Gather attached child actors (windows, workbench, order book/counter) BEFORE moving parent,
    # capturing each child's exact local transform relative to Village_09_Gunshop.
    children = []
    for a in all_actors:
        if a == site:
            continue
        tags = set(map(str, a.tags))
        parent = a.get_attach_parent_actor()
        if parent == site or 'VillageGunshop.Window' in tags or (
            'VillageGunshop.Service' in tags and a.get_actor_label() != 'Village_TradeWaypost_Gunshop'
        ):
            local_tf = ue.MathLibrary.compose_transforms(a.get_actor_transform(), inv_old)
            children.append((a, local_tf))

    # Move main site rigidly (all 157 ruin + restored + lighting + hanging-sign components follow).
    site.modify()
    site.set_actor_transform(new_tf, False, True)

    # Sync all child actors to exact rigid transforms relative to the relocated site.
    keep = ue.AttachmentRule.KEEP_WORLD
    moved_children = []
    for child, local_tf in children:
        world_tf = ue.MathLibrary.compose_transforms(local_tf, new_tf)
        child.modify()
        child.attach_to_actor(site, 'None', keep, keep, keep, False)
        child.set_actor_transform(world_tf, False, True)
        moved_children.append(child.get_actor_label())

    # Move BuildingDaylight interior vision volume to match new site transform.
    vision = next((a for a in all_actors if a.get_actor_label().startswith('Village_InteriorVision_09_')), None)
    if not vision:
        raise RuntimeError('Cannot locate Village_InteriorVision_09_ actor')
    vision.modify()
    vision.set_actor_transform(new_tf, False, True)

    # Relocate roadside Gunshop trade waypost to the west main-road / south-lane fork.
    waypost = next((a for a in all_actors if a.get_actor_label() == 'Village_TradeWaypost_Gunshop'), None)
    if waypost:
        waypost.modify()
        waypost.set_actor_transform(
            ue.Transform(location=WAYPOST_TARGET_LOC, rotation=ue.Rotator(yaw=WAYPOST_TARGET_YAW)),
            False, True
        )

    # Clear ground scatter inside the new Gunshop footprint & doorway approach.
    cleared = clear_scatter_in_boxes(actors, [
        (-4050.0, 2480.0, -2850.0, 3700.0),  # New gunshop shell + approach flags
        (-4020.0, 240.0, -3860.0, 420.0),    # New waypost footing
    ])

    return dict(
        old_location_cm=[round(float(old_tf.translation.x), 1), round(float(old_tf.translation.y), 1), round(float(old_tf.translation.z), 1)],
        new_location_cm=[GUNSHOP_TARGET_LOC.x, GUNSHOP_TARGET_LOC.y, GUNSHOP_TARGET_LOC.z],
        new_yaw_deg=GUNSHOP_TARGET_YAW,
        moved_children=sorted(moved_children),
        vision_actor=vision.get_actor_label(),
        waypost_location_cm=[WAYPOST_TARGET_LOC.x, WAYPOST_TARGET_LOC.y, WAYPOST_TARGET_LOC.z] if waypost else None,
        waypost_yaw_deg=WAYPOST_TARGET_YAW if waypost else None,
        cleared_scatter=cleared,
    )
