"""Native Normandy modules, in the local doorway frame of each repaired shop (cm)."""
from math import ceil
from pathlib import Path
import sys

import unreal as u

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'VillageBakery'))
from shell_geometry import EAVE, WALLS, roof_z

KIT = '/Game/UnrealNormandy/StaticMeshes/'
HILLS = '/Game/WorldGeneration/TemperateHills/'
BAKERY_BAYS = HILLS + 'VillageBakery/Architecture/SM_Bakery_NativeOpeningBays'
GUNSHOP_EDGES = HILLS + 'VillageGunshop/Architecture/SM_Gunshop_DeckEdgeAndThreshold'
BOARDS = KIT + 'SM_WoodenFloor_00A'


def bays(start, end, openings):
    """Give each opening its jambs; short intervening piers are shared by adjacent bays."""
    margin = 57.
    windows = sorted(openings)
    cursor = start
    for i, opening in enumerate(windows):
        a, b = opening[:2]
        left = max(start, a - margin)
        if i and a - windows[i-1][1] < 2 * margin + 115:
            left = .5 * (a + windows[i-1][1])
        elif left - cursor < 115:
            left = cursor
        right = min(end, b + margin)
        if i + 1 < len(windows) and windows[i+1][0] - b < 2 * margin + 115:
            right = .5 * (b + windows[i+1][0])
        elif i + 1 == len(windows) and end - right < 115:
            right = end
        if left > cursor:
            yield cursor, left, None
        yield left, right, opening
        cursor = right
    if cursor < end:
        yield cursor, end, None


def wall_layout():
    for axis, line, start, end, openings in WALLS:
        yaw = (0 if line == 0 else 180) if axis == 'X' else (-90 if line < 0 else 90)
        sign = 1 if yaw in (0, 90) else -1
        frame = u.Transform(location=(0, line, 0) if axis == 'X' else (line, 0, 0),
                            rotation=u.Rotator(yaw=yaw))
        for low, high in ((-12., 303.), (303., EAVE)):
            windows = [o for o in openings if low <= o[2] < high]
            for a, b, hole in bays(start, end, windows):
                left, right = sorted((a*sign, b*sign))
                if hole:
                    x, y = sorted((hole[0]*sign, hole[1]*sign))
                    hole = (x, y, hole[2], hole[3])
                yield frame, left, right, low, high, hole


def bakery_modules():
    rows = [(BAKERY_BAYS, u.Transform(), True)]
    for frame, left, right, low, high, hole in wall_layout():
        if hole:
            continue
        count = max(1, round((right-left)/300.))
        span = (right-left)/count
        ground = low < 0
        path = KIT + ('SM_H_StoneWall_00A' if ground else 'SM_H_OldWall_00A')
        for i in range(count):
            t = u.Transform(location=(left+(i+.5)*span, 0, (low+high)*.5),
                            scale=(span/290., .65 if ground else .79, (high-low)/290.))
            rows.append((path, u.MathLibrary.compose_transforms(t, frame), False))
    for x, y, yaw in ((-392,0,180),(392,0,-90),(-392,902,90),(392,902,0)):
        for lo, hi in ((-12.,303.),(303.,EAVE)):
            rows.append((KIT+'SM_H_WallCorner_00A', u.Transform(location=(x,y,(lo+hi)*.5),
                         rotation=u.Rotator(yaw=yaw), scale=(.74,.74,(hi-lo)/297.)), False))
    ridge = roof_z(0)-13.
    for y in (0,902):
        for x, yaw in ((-195.5,0),(195.5,180)):
            rows.append((KIT+'SM_H_OldWall_Triangle_00A', u.Transform(location=(x,y,(EAVE+ridge)*.5),
                         rotation=u.Rotator(yaw=yaw), scale=(391./298., .65, (ridge-EAVE)/298.)), False))
    return rows


def floor_tiles():
    """Keep each storey's grain and tile pitch continuous across the stair opening."""
    for loft in (False, True):
        x0, x1, y0, y1 = (-476.,476.,11.,901.) if loft else (-475.5,475.5,-13.,900.)
        w, d = (x1-x0)/3., (y1-y0)/3.
        floor_z, thickness = (340.,9.) if loft else (0.,19.)
        for row in range(3):
            shift = .5 if row % 2 else 0.
            for col in range(ceil(3 + shift)):
                x, y = x0+(col-shift)*w, y0+row*d
                l, r, b, t = max(x,x0), min(x+w,x1), y, y+d
                frame = u.Transform(location=(x+w*.5,y+d*.5,floor_z-thickness), scale=(w/300.,d/300.,thickness/20.))
                rectangles = [(l,r,b,t)]
                if loft and r>319. and b<720. and t>135.:
                    rectangles = [(l,min(r,319.),b,t),(max(l,319.),r,b,min(t,135.)),
                                  (max(l,319.),r,max(b,720.),t)]
                cuts = [box for box in rectangles if box[1]-box[0]>.01 and box[3]-box[2]>.01]
                complete = len(cuts)==1 and all(abs(a-b)<.01 for a,b in zip(cuts[0],(x,x+w,y,y+d)))
                if cuts:
                    yield frame, None if complete else cuts


def gunshop_modules():
    return [(GUNSHOP_EDGES, u.Transform(), True)] + [(BOARDS, t, False) for t, cuts in floor_tiles() if cuts is None]


def place_modules(place, rows):
    # The shop installers accept bounds-centred bottom pivots; Normandy meshes
    # retain their original, often asymmetric model pivots.
    bounds = {}
    for path, pose, solid in rows:
        if path not in bounds:
            asset = u.load_asset(path)
            if not asset:
                raise RuntimeError('Missing house module '+path)
            box = asset.get_bounding_box()
            centre = (box.min + box.max)*.5
            bounds[path] = (u.Vector(centre.x,centre.y,box.min.z), box.max-box.min)
        pivot, span = bounds[path]
        p = u.MathLibrary.transform_location(pose, pivot)
        s = span*pose.scale3d
        place(path.rsplit('/',1)[1],path,(p.x,p.y,p.z),(s.x,s.y,s.z),pose.rotation.rotator().yaw,solid)
