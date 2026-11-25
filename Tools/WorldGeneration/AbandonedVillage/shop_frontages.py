"""Repaired public thresholds and flagstones shared by the shop installers and terrain author."""
from layout_geometry import nearest, rotate


# Actor-local centimetres. Columns are X, Y, length, width, heading and thickness.
BAKERY_FLAGS = (
    (-31,-35,78,49,8,7), (44,-36,67,45,-7,7), (8,-84,75,54,17,7),
    (55,-119,59,44,-21,6), (93,-147,60,40,24,6), (148,-146,48,35,-13,6),
    (207,-131,63,47,24,6), (282,-124,48,36,7,5), (331,-109,61,42,-19,6),
    (387,-78,70,47,21,7), (415,-20,59,36,-9,6), (426,45,51,34,17,5),
    (-48,-114,57,35,-21,6), (-87,-174,52,41,14,6), (-126,-237,42,31,-9,5),
    (-169,-283,37,28,22,5))
GUNSHOP_FLAGS = (
    (-8,-76,62,38,-8), (-61,-94,52,41,11), (-94,-126,45,35,-21),
    (-141,-139,48,32,8), (-175,-152,35,23,-17))


def public_frame(house, shape):
    x,y = shape['center']
    if house[0]=='06':
        yaw = house[5]-180.
        dx,dy = rotate(.21,-4.5,yaw)
        return (x+dx,y+dy),yaw
    if house[0]=='09':
        return (x,y-4.5),0.
    raise ValueError('No replacement threshold for lot '+house[0])


def flag_walks(house,shape,plan):
    origin,yaw = public_frame(house,shape)
    streets = [(r['points'],r['width']) for r in plan['roads']]
    def walk(flags, lanes):
        points=[origin]
        for x,y,*_ in flags:
            dx,dy=rotate(x/100.,y/100.,yaw)
            points.append((origin[0]+dx,origin[1]+dy))
        points.append(nearest(points[-1],lanes))
        return points
    if house[0]=='06':
        # The paired stones either side of the landing feed a common centre.
        return [walk(BAKERY_FLAGS[2:12],[streets[0]]),
                walk(BAKERY_FLAGS[12:],streets)]
    return [walk(GUNSHOP_FLAGS,streets)]
