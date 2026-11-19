"""Seamless stoneware PBR maps. Masks are occlusion, glazed roughness, dry clay roughness."""
from pathlib import Path

import numpy as np
from PIL import Image


OUT = Path(__file__).resolve().parents[4] / 'SourceAssets/HillsVillageTavern/Service'
SIZE = 2048
RNG = np.random.default_rng(131119)
coord = np.arange(SIZE, dtype=np.float32) / SIZE
x, y = coord[None, :], coord[:, None]
tau = 2 * np.pi


def noise(columns, rows):
    grid = RNG.uniform(-1., 1., (rows, columns)).astype(np.float32)
    ix, iy = (x*columns).astype(int), (y*rows).astype(int)
    dx, dy = x*columns-ix, y*rows-iy
    dx, dy = dx*dx*(3.-2.*dx), dy*dy*(3.-2.*dy)

    def corner(a, b):
        return grid[(iy+b) % rows, (ix+a) % columns]

    top = corner(0, 0)*(1.-dx) + corner(1, 0)*dx
    bottom = corner(0, 1)*(1.-dx) + corner(1, 1)*dx
    return (top*(1.-dy) + bottom*dy).astype(np.float32)


def inclusions(number, size_range):
    """Scatter elliptical oxide grains with soft fired halos, including across tile seams."""
    core = np.zeros((SIZE, SIZE), np.float32)
    halo = np.zeros_like(core)
    for _ in range(number):
        cx, cy = RNG.integers(0, SIZE, 2)
        radius = RNG.uniform(*size_range)
        elongation = RNG.uniform(.73, 1.35)
        span = int(np.ceil(radius*3.2))
        axis = np.arange(-span, span+1)
        xx, yy = np.meshgrid(axis, axis)
        d2 = (xx*elongation/radius)**2 + (yy/(radius*elongation))**2
        index = np.ix_((cy+axis) % SIZE, (cx+axis) % SIZE)
        strength = RNG.uniform(.45, 1.)
        core[index] = np.maximum(core[index], np.exp(-d2*2.7)*strength)
        halo[index] = np.maximum(halo[index], np.exp(-d2*.48)*strength)
    return core, halo


def save(name, r, g, b):
    pixels = np.stack((r, g, b), axis=-1).clip(0., 1.)
    Image.fromarray(np.rint(pixels*255.).astype(np.uint8)).save(OUT/(name+'.png'))


def make_surfaces():
    OUT.mkdir(exist_ok=True, parents=True)
    firing = .65*noise(5, 7) + .35*noise(15, 22)
    slip = noise(43, 26)
    grit = noise(340, 360)
    # Short flowing glaze runs end at different heights. The dry foot uses its own roughness.
    tide = .69*noise(30, 6) + .31*noise(56, 15)
    pooling = np.clip((tide+.21*firing-.13)*1.48, 0., 1.)
    # Light finger/tool pressure on the wheel makes fine, interrupted horizontal courses.
    phase = y*36. + .14*np.sin(tau*x*2) + .24*np.sin(tau*y*4) + .17*slip
    groove = np.maximum(0., np.cos(tau*phase))**6 * (.45+.43*noise(12, 9))
    iron, bloom = inclusions(2400, (1.2, 4.1))
    pin, lip = inclusions(620, (1.5, 3.3))
    rim_of_pinhole = np.maximum(0., lip-1.25*pin)
    colour = .875 + .063*firing + .023*slip + .018*grit
    colour -= .056*pooling + .024*groove + .34*iron + .068*bloom + .09*pin
    # Mineral-rich spots warm towards the centre. Keep broad colour free of lighting.
    save('T_KilnAlbedo', colour+.022*firing+.019*bloom, colour,
         colour-.018*firing-.042*bloom-.029*pooling)

    glazed = .355-.17*pooling+.055*firing+.032*slip+.032*grit+.21*iron+.23*pin+.04*groove
    biscuit = .782+.075*grit+.047*slip+.043*firing+.12*pin+.062*iron+.025*groove
    save('T_KilnMasks', .993-.11*pin-.044*iron-.019*groove, glazed, biscuit)
    # Height is in texels. Use the same mineral inclusions in all three maps.
    height = .52*grit+.43*slip-.83*groove+.77*pooling+.34*iron-1.35*pin+.32*rim_of_pinhole
    nx = -.5*(np.roll(height, -1, 1)-np.roll(height, 1, 1))
    ny = .5*(np.roll(height, -1, 0)-np.roll(height, 1, 0))
    inv = 1./np.sqrt(1.+nx*nx+ny*ny)
    save('T_KilnNormal', .5+.5*nx*inv, .5+.5*ny*inv, .5+.5*inv)


if __name__ == '__main__':
    make_surfaces()
