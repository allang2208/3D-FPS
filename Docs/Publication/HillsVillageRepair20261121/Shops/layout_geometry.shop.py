"""Shop assembly dependencies extracted from AbandonedVillage/layout_geometry.py."""
import math


def rotate(x, y, degrees):
    angle = math.radians(degrees)
    return x * math.cos(angle) - y * math.sin(angle), x * math.sin(angle) + y * math.cos(angle)


def house_geometry(house, pieces, scale):
    _, _, _, x, y, yaw = house
    floors = [part for part in pieces if 'SM_WoodenFloor_' in part['mesh']]
    # The source walking surface and its box collision are at local Z=20 cm.
    # Nanite/displacement bounds extend higher and cannot be used as the floor datum.
    floor = max(part['pos'][2] + 20 * part['scale'][2] for part in floors)
    lo = [min(part['pos'][axis]-150*part['scale'][axis] for part in floors) for axis in (0, 1)]
    hi = [max(part['pos'][axis]+150*part['scale'][axis] for part in floors) for axis in (0, 1)]
    center = [(a+b)*.5 for a, b in zip(lo, hi)]
    offset = rotate(center[0]*scale/100, center[1]*scale/100, yaw)
    half = [(b-a)*scale/200 + .35*scale for a, b in zip(lo, hi)]
    door = next(part for part in pieces if 'OldWall_Door' in part['mesh'])
    entry_offset = rotate(door['pos'][0]*scale/100, door['pos'][1]*scale/100, yaw)
    normal = rotate(0, -1, yaw+door['rot'][1])
    entry = (x+entry_offset[0], y+entry_offset[1])
    step = (entry[0]+normal[0]*1.5, entry[1]+normal[1]*1.5)
    roof = max(part['center'][2]+part['extent'][2] for part in pieces if 'Wall' in part['mesh'])
    return dict(floor=floor, half=half, center=(x+offset[0], y+offset[1]), angle=yaw,
                entry=entry, step=step, normal=normal, room_min=[lo[0], lo[1], floor],
                room_max=[hi[0], hi[1], roof])


def plot_geometry(house, pieces, plan):
    scale = plan.get('house_scale', 1.)
    shape = house_geometry(house, pieces, scale)
    tavern = plan.get('tavern', {})
    if house[0] == tavern.get('house'):
        # Enlarge around the existing threshold. The street apron and its approach stay registered.
        growth = tavern['footprint_scale']
        shape['center'] = tuple(door + (center - door) * growth
                                for center, door in zip(shape['center'], shape['entry']))
        shape['half'] = [r * growth for r in shape['half']]
    return shape
