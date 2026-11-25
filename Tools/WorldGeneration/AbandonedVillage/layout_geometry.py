"""Shared metric house geometry for the village mesh assembly, access paths and exclusions."""
import math


def rotate(x, y, degrees):
    angle = math.radians(degrees)
    return x * math.cos(angle) - y * math.sin(angle), x * math.sin(angle) + y * math.cos(angle)


def nearest(point, paths):
    best, result = math.inf, None
    for points, _ in paths:
        for a, b in zip(points, points[1:]):
            dx, dy = b[0]-a[0], b[1]-a[1]
            t = min(1, max(0, ((point[0]-a[0])*dx + (point[1]-a[1])*dy)/(dx*dx+dy*dy)))
            q = (a[0]+dx*t, a[1]+dy*t)
            distance = math.dist(point, q)
            if distance < best:
                best, result = distance, q
    return result


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


def approach_path(house, shape, plan, streets):
    turns = plan.get('house_approaches', {}).get(house[0], [])
    points = [shape['entry'], shape['step'], *turns]
    points.append(nearest(points[-1], streets))
    return points, 1.8


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
        if inn := tavern.get('inn'):
            nx,ny=shape['normal']
            back=(-nx*inn['setback_m'],-ny*inn['setback_m'])
            side=rotate(inn.get('east_shift_m',0),0,house[5]-90.)
            back=tuple(a+b for a,b in zip(back,side))
            anchor=tuple(a+b for a,b in zip(shape['center'],back))
            shift=rotate(-inn['west_extension_m']*.5,inn.get('rear_range_m',0)*.5,house[5]-90.)
            shape['shell_center']=anchor
            shape['center']=tuple(a+b for a,b in zip(anchor,shift))
            shape['half'][1]+=inn['west_extension_m']*.5
            shape['half'][0]+=inn.get('rear_range_m',0)*.5
            for key in ('entry','step'):
                shape[key]=tuple(a+b for a,b in zip(shape[key],back))
    return shape


def house_paths(plan, kit):
    streets = [(road['points'], road['width']) for road in plan['roads']]
    result = []
    for house in plan['houses']:
        shape = plot_geometry(house, kit[house[2]], plan)
        result.append(approach_path(house, shape, plan, streets))
    return result


def wall_segments(plan):
    """Keep terrain skirts consistent with the actual native wall widths."""
    for yard in plan['yard_walls']:
        native = yard.get('native_instances', [])
        for index, piece in enumerate(yard['pieces']):
            yield piece, native[index]['half_width_m'] if native else .26
