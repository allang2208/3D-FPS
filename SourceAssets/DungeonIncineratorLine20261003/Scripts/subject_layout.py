"""Space the retained treatment rooms by their full rigid footprints."""
import math

REVISION = 'full_room_footprints_20261003'


def transform(position, pose):
    a = math.radians(pose['yaw'])
    x, y, z = position
    o = pose['position']
    return [x * math.cos(a) - y * math.sin(a) + o[0],
            x * math.sin(a) + y * math.cos(a) + o[1], z + o[2]]


def placements(modules, sequence):
    # The support room has a discovery wing beyond its exit. Aligning ports
    # alone puts that wing inside the observation stairs in the next room.
    result = [dict(id=sequence[0], position=[0, 0, 0], yaw=0)]
    for previous_id, next_id, name in zip(sequence, sequence[1:],
                                         ['SupportHallLink', 'HallPurificationLink']):
        previous = result[-1]
        end = transform(modules[previous_id]['ports'][1]['position'], previous)
        entry = modules[next_id]['ports'][0]['position']
        previous_edge = previous['position'][0] + modules[previous_id]['max'][0]
        minimum_length = previous_edge + 70 - (end[0] - entry[0] + modules[next_id]['min'][0])
        length = max(400, math.ceil(minimum_length / 80) * 80)
        segments = ['Transit'] * (length // 400) + ['Threshold'] * ((length % 400) // 80)
        for index, identity in enumerate(segments):
            pose = dict(id=identity, name=name if index == 0 else name + '_Extension' + str(index),
                        position=end, yaw=90)
            result.append(pose)
            end = transform(modules[identity]['ports'][1]['position'], pose)
        result.append(dict(id=next_id, position=[end[i] - entry[i] for i in range(3)], yaw=0))
    return result
