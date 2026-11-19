"""Bake a shared UV atlas of finished kitchen hardwood. Dimensions are in cm."""
from pathlib import Path

import numpy as np
from PIL import Image


OUT = Path(__file__).resolve().parents[4] / 'SourceAssets/HillsVillageTavern/EatingUtensils'
SIZE = 1024
PREFIX = 'T_TavernEatingWood_'


def surface(x, y, z, species, polish):
    # Sample the same piece of timber on each side of an implement. Bowed annual
    # rings change direction across the spoon and all vessels follow the long axis.
    line = y + .025*x + .076*np.sin(x*.42 + z) + .028*np.sin(x*1.08 + 2*y)
    deep = z + .045*np.sin(x*.65 + y*1.33)
    radial = np.hypot(line + .9, deep + 2.9)
    rings = .5 + .5*np.sin(16.8*radial + .38*np.sin(4.3*radial))
    late = rings**5
    fiber = np.zeros_like(radial)
    pore = np.zeros_like(radial)
    rng = np.random.default_rng(2917 + species)
    for frequency in (32, 48, 61, 89, 127, 153):
        offset, angle, phase, rate = rng.uniform(0, 6, 4)
        vein = np.sin(frequency*(line*np.cos(angle) + deep*np.sin(angle)) + offset
                      + .57*np.sin(.71*x + 4*line + phase))
        fiber += vein/6
        opening = np.maximum(0, vein)**12
        pore += opening * np.maximum(0, np.cos(x*(3+rate) + 2.7*line + phase))**5 / 4
    mottle = .57*np.sin(x*.83+line*3) + .43*np.sin(x*.37+deep*2.7)
    if species:
        base, shade = (164., 118., 70.), (20., 17., 12.)
    else:
        base, shade = (128., 82., 46.), (24., 19., 13.)
    depth = .44*late + .4*pore - .28*fiber - .12*mottle
    color = np.asarray(base) - depth[..., None]*np.asarray(shade)
    color += polish[..., None]*np.array([5., 3.1, 1.2])
    rough = .525 - .175*polish + .027*late + .075*pore - .031*fiber
    relief = (.0015*fiber - .0041*pore - .0018*late) * (1-.49*polish)
    return color, rough, relief


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    u = (np.arange(SIZE, dtype=float)[None, :] + .5)/SIZE
    v = (np.arange(SIZE, dtype=float)[:, None] + .5)/SIZE
    color = np.empty((SIZE, SIZE, 3))
    rough = np.empty((SIZE, SIZE))
    relief = np.empty_like(rough)
    physical_u = np.empty((SIZE, 1))
    physical_v = np.empty_like(physical_u)
    # Use extra stock beyond each island as a mip gutter.
    bands = ((0., .043, 'end', 0), (.043, .219, 'stick', 0), (.219, .395, 'stick', 1),
             (.395, .7, 'upper', 0), (.7, 1., 'lower', 0))
    for lo, hi, kind, part in bands:
        rows = ((v>=lo) & (v<hi)).ravel()
        frac = (v[rows] - lo)/(hi-lo)
        if kind == 'end':
            radius = np.hypot((u-.5)*2.4, (frac-.5)*.8 + .22)
            late = (.5+.5*np.sin(radius*48 + .4*np.sin(u*24)))**4
            c = np.array([123, 81, 47])-late[..., None]*np.array([12, 10, 8])
            r, h, du, dv = .51+.05*late, -.0017*late, 2.4, .8
        elif kind == 'stick':
            a = 2*np.pi*(frac-.05)/.90
            x = (u-.035)*23/.93
            y = (1.65*part + .34*np.cos(a)) + 0*x
            z = .32*np.sin(a) + 0*x
            polish = (.30 + .61*np.exp(-((x-6.8)/5.5)**2)
                      + .40*np.exp(-((x-20.5)/2.3)**2))*np.ones_like(y)
            c, r, h = surface(x, y, z, 0, np.clip(polish,0,1))
            du, dv = 23/.93, 2.12/.90
        else:
            y = (frac-.5)*5.45
            x = (u-.045)*17.7/.91
            z = .19*np.cos(y*1.23 + .38*x)
            if kind == 'lower':
                z = z - .24*np.maximum(0, 1-(y/2.55)**2)
            polish = .29 + .45*np.exp(-((x-4.7)/4)**2) + .39*np.exp(-((x-14.4)/2.0)**2-(y/1.7)**2)
            c, r, h = surface(x, y, z, 1, polish)
            du, dv = 17.7/.91, 5.45
        color[rows], rough[rows], relief[rows] = c, r, h
        physical_u[rows], physical_v[rows] = du/SIZE, dv/((hi-lo)*SIZE)
    dh_v, dh_u = np.gradient(relief)
    dx, dy = -dh_u/physical_u, dh_v/physical_v
    norm = np.sqrt(1+dx*dx+dy*dy)
    normal = np.stack((dx/norm, dy/norm, 1/norm), -1)*.5+.5
    def save(name, pixels):
        data = np.clip(np.rint(pixels[::-1]),0,255).astype('uint8')
        Image.fromarray(data).save(OUT/(PREFIX+name+'.png'))
    save('Color',color)
    save('Roughness',rough*255)
    save('Normal',normal*255)


if __name__ == '__main__':
    main()
