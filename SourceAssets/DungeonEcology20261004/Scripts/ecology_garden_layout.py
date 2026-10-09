"""Metre-space garden beds and clear pedestrian routes, shared by authoring stages."""
import math

PATHS = [
    (1.25, [(-24, 0), (-17, 0), (-12, -2.5), (-5, -3.4), (5, -3.4), (12, -1.8), (17, 0), (24, 0)]),
    (1.10, [(-17, 0), (-15, 4.7), (-8, 7.3), (0, 8.4), (8, 7.3), (16, 4.7), (17, 0)]),
    (1.0, [(-17, 0), (-18.5, 3.8), (-17.8, 6.9)]),
]
DRY_RECTS = [(-24.5, 6.35, -15.5, 17), (-13.85, 3.45, -10.55, 16.5),
             (10.55, 3.45, 13.85, 16.5), (-24.5, 12.05, 24.5, 17),
             (-24.5, -.2, -9.7, 12.2)]


def segment_distance(x, y, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0., min(1., ((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)))
    return math.hypot(x-a[0]-t*dx, y-a[1]-t*dy)


def bed_margin(x, y):
    angle = math.atan2(y/12.5, x/21.6)
    radial = math.sqrt((x/21.6)**2+(y/12.5)**2)
    # Smooth irregular perimeter, wholly inside the clear wall-side apron.
    margin = (1.-radial)*12.5 + .18*math.sin(angle*5) + .10*math.cos(angle*9)
    for half_width, points in PATHS:
        margin = min(margin, min(segment_distance(x, y, a, b) for a, b in zip(points, points[1:]))-half_width)
    for x0, y0, x1, y1 in DRY_RECTS:
        if x0 <= x <= x1 and y0 <= y <= y1:
            return -min(x-x0, x1-x, y-y0, y1-y)
        margin = min(margin, math.hypot(max(x0-x, 0, x-x1), max(y0-y, 0, y-y1)))
    return margin


def bed_height(x, y, sample=.5):
    edge = min(1., max(0., bed_margin(x, y))/.8)
    mound = .07 + .075*(.5+.5*math.sin(x*.32+y*.23)) + .035*math.cos(y*.55-x*.22)
    return .023 + edge*(mound + (sample-.5)*.018)
