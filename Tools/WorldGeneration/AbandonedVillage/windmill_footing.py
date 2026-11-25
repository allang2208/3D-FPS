"""Local terrain wear at house 05. All lengths are village-local metres."""
import json
from pathlib import Path

import numpy as np
from PIL import Image

from layout_geometry import approach_path, plot_geometry
from village_tread import ramp, soil_variation, tread, window


def dress_ground(packed, verge, plan, kit):
    house = next(h for h in plan['houses'] if h[0] == '05')
    shape = plot_geometry(house, kit[house[2]], plan)
    streets = [(road['points'], road['width']) for road in plan['roads']]
    approach, _ = approach_path(house, shape, plan, streets)
    entry_x, entry_y = shape['entry']
    nx, ny = shape['normal']
    radius = 3.765  # radius of D01 at the sill
    cx, cy = entry_x - radius*nx, entry_y - radius*ny
    ex, ey = plan.get('surface_extent_m', plan['extent_m'])
    w, h = packed.size
    px = ((np.arange(w)[None, :] + .5) / w - .5) * (2*ex)
    py = ((np.arange(h)[:, None] + .5) / h - .5) * (2*ey)
    # End at the existing back lane. The surface outside the footprint is
    # inherited directly from the source image, including other shop edits.
    margin = 2.
    reach = 6.4
    bounds = (min(cx-reach, *(p[0]-margin for p in approach)),
              min(cy-reach, *(p[1]-margin for p in approach)),
              max(cx+reach, *(p[0]+margin for p in approach)),
              max(cy+reach, *(p[1]+margin for p in approach)))
    (ys, xs), x, y = window(px, py, bounds)
    local_x = (x-cx)*ny - (y-cy)*nx
    local_y = (x-cx)*nx + (y-cy)*ny
    toe = np.hypot(local_x, local_y) - radius
    broad = soil_variation(x, y, 2.04, 5057)
    mid = soil_variation(x, y, .78, 5061)
    flecks = soil_variation(x, y, .27, 5051)

    def pocket(at_x, at_y, span_x, span_y):
        return np.exp(-(((local_x-at_x)/span_x)**2 + ((local_y-at_y)/span_y)**2))

    # At the exposed roadside face the plinth stays largely dry. Runoff soaks
    # two sheltered bays; broken stretches between them keep the turf intact.
    rear = pocket(-2.10,-3.50,2.45,1.93)
    flank = pocket(3.64,-.95,1.65,2.33)
    western_toe = pocket(-3.64,1.75,1.38,1.62)
    shelter = np.maximum.reduce([rear, flank*.89, western_toe*.57])
    outside = ramp((toe+.17)/.24)
    depth = .29 + .93*shelter + .37*broad + .24*mid
    wick = outside*ramp((depth-toe+.26)/.65)
    soil = wick*np.clip(.27+.59*shelter+.15*mid+.09*flecks, .05, .86)

    # Carry sacks over a slightly widened landing, then back onto the narrow
    # approach. The existing footway texture takes over at the lane junction.
    widths = np.linspace(.91, .41, len(approach))
    line = [(p[0], p[1], width) for p, width in zip(approach, widths)]
    track = tread(x, y, line, .09*mid+.045*flecks)
    landing = pocket(.42,4.14,1.12,.83)
    walked = np.maximum(ramp((track+.32+.15*mid+.06*flecks)/.68), landing)
    walked *= ramp((local_y-radius+.18)/.28)
    soil = np.maximum(soil, walked*np.clip(.84+.09*mid+.07*flecks, .55, .99))

    # A few mineral lenses break through at the landing edge and along the
    # drip line. B is the signed road-edge channel, +/- 2.5 m in the material.
    bed = np.maximum(pocket(.98,4.30,.65,.64), pocket(-3.69,-1.45,.83,.92)*.82)
    exposure = np.clip((.83*bed+.31*wick+.12*mid+.10*flecks)*outside, 0., 1.)
    stone = ramp((exposure-.22)/.65)*.52

    # Put tufts just past the damp strip. Keep the road shoulder and door
    # landing clear even where the existing rectangular ruin footprint cut turf.
    protection = road_clearance(x, y, streets)
    verge_edge = ramp((1.58+.47*shelter+.46*broad-toe+.17*mid)/.97)
    turf = outside*verge_edge*np.clip(.12+.66*shelter+.35*broad+.19*mid,0.,.89)
    turf *= (1.-.67*wick)*(1.-walked)*ramp((protection-.04)/.55)
    turf_cap = 1.-walked*.98

    def byte(field):
        return np.rint(np.clip(field,0.,1.)*255.).astype('uint8')

    box = (xs.start, ys.start, xs.stop, ys.stop)
    channels = np.array(packed.crop(box))
    channels[:,:,1] = np.maximum(channels[:,:,1], byte(soil))
    channels[:,:,2] = np.maximum(channels[:,:,2], byte(stone))
    channels[:,:,3] = 255-np.minimum(np.maximum(255-channels[:,:,3],byte(turf)),byte(turf_cap))
    packed.paste(Image.fromarray(channels), box)

    # Reuse the same metric field for the lower-resolution instance cover.
    # Empty/white outside the crop are the neutral values for max and min.
    def low_field(field, fill):
        layer = Image.new('L', packed.size, fill)
        layer.paste(Image.fromarray(byte(field)), box)
        return np.asarray(layer.resize(verge.size, Image.Resampling.BOX))

    updated = np.minimum(np.maximum(np.asarray(verge), low_field(turf,0)),low_field(turf_cap,255))
    return packed, Image.fromarray(updated)


def road_clearance(x, y, streets):
    distance = np.full((y.shape[0], x.shape[1]), np.inf)
    for points, width in streets:
        distance = np.minimum(distance, -tread(x,y,[(*p,width*.5) for p in points]))
    return distance


if __name__ == '__main__':
    # A scoped update starts from today's actual images instead of rebuilding
    # unrelated streets or replacing other authors' painted pixels.
    src = Path(__file__).resolve().parents[3] / 'SourceAssets/TemperateHillsVillage'
    mask_path, verge_path = src/'RoadMask.png', src/'VergeTurf.raw'
    plan = json.loads((src/'layout.json').read_text(encoding='utf-8'))
    kit = json.loads((src/'house-pieces.json').read_text(encoding='utf-8'))
    with Image.open(mask_path) as im:
        mask = im.convert('RGBA')
    verge = Image.frombytes('L', (460,320), verge_path.read_bytes())
    mask, verge = dress_ground(mask, verge, plan, kit)
    mask.save(mask_path)
    verge_path.write_bytes(verge.tobytes())
