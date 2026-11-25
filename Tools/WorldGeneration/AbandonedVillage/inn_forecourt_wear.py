"""Paint only the western approach to the inn on the shared village terrain mask."""
import math

import numpy as np
from PIL import Image

from village_tread import ramp, soil_variation, tread, window


def paint(packed, plan):
    site = plan['tavern_forecourt']
    ox, oy = site['origin']
    ex, ey = plan['surface_extent_m']
    width, height = packed.size
    x = ((np.arange(width)[None, :] + .5) / width - .5) * (2 * ex)
    y = ((np.arange(height)[:, None] + .5) / height - .5) * (2 * ey)
    region, x, y = window(x, y, (ox-9., oy-8., ox+7., oy+4.))
    c, s = math.cos(math.radians(site['yaw'])), math.sin(math.radians(site['yaw']))
    along = (x-ox)*c + (y-oy)*s
    across = (y-oy)*c - (x-ox)*s
    loam = soil_variation(x, y, 1.38, 6203)
    grit = soil_variation(x, y, .31, 6217)
    # A soft margin runs past the old rectangular beds and breaks into the verge.
    dx = abs(along+.35)-4.60
    dy = abs(across+2.38)-1.72
    boundary = np.hypot(np.maximum(dx, 0), np.maximum(dy, 0)) + np.minimum(np.maximum(dx,dy), 0)
    cover = ramp((1.03-boundary+.27*loam+.12*grit)/.96)
    walk = tread(x,y,site['trail'])
    wear = ramp((walk+.41+.13*loam)/.90)
    shoulder = np.exp(-((walk+.43+.22*loam)/(.42+.09*grit))**2)
    lane = plan['roads'][3]
    lane_wear = ramp((tread(x,y,[(*p,lane['width']/2) for p in lane['points']])+.30)/.75)
    traffic = np.maximum(wear,lane_wear)
    ochre = np.clip(.52+.17*loam+.075*grit+.34*traffic, .23, .96)
    fines = np.clip(.23+.10*loam+.11*grit+.25*shoulder+.095*traffic, .07, .67)
    pixels = np.array(packed.convert('RGBA'))
    tile = pixels[region]
    for index, target in ((1,ochre),(2,fines)):
        tile[:,:,index] = np.rint(tile[:,:,index]*(1-cover)+255*target*cover).astype('uint8')
    return Image.fromarray(pixels)
