"""Produce original periodic PBR data from one physical surface model. No render."""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates, gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT/'Config/surface.json').read_text())
OUT = ROOT/'Authored/Textures'
OUT.mkdir(parents=True, exist_ok=True)
N = CFG['resolution']
rng = np.random.default_rng(CFG['seed'])
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
u, v = xx / N, yy / N


def noise(cells):
    values = rng.random((cells, cells), dtype=np.float32)
    return map_coordinates(values, [v*cells, u*cells], order=3, mode='grid-wrap', prefilter=True)


def smooth(a, b, x):
    f = np.clip((x-a)/(b-a), 0, 1)
    return f*f*(3-2*f)


macro = noise(5)
meso = noise(17)
grain = noise(181)
fine = noise(509)
warp = noise(11)
erosion = noise(61)
pores = smooth(.66, .88, noise(251)) * smooth(.37, .64, meso)
aggregate = smooth(.60, .85, grain)
# Signed irregular islands define material coverage. The same height competition
# is used by colour, roughness and relief; no unrelated albedo cloud mask.
core = .31 + (meso-.5)*.16 + (grain-.5)*.10 + aggregate*.06 - pores*.13
skim_height = .55 + (meso-.5)*.07 + (fine-.5)*.012
coverage = macro + (erosion-.5)*.14 + (warp-.5)*.13
skim = smooth(.425, .48, coverage + (skim_height-core)*.07)
comb = np.zeros_like(core)
scratches = np.zeros_like(core)
# Each trowel stroke is a short curved packet with its own spacing, fade and
# abrasion. Periodic deltas keep the field tileable in both coordinates.
for _ in range(11):
    cx, cy = rng.random(2)
    dx, dy = (u-cx+.5)%1-.5, (v-cy+.5)%1-.5
    angle = rng.uniform(-.72, .72)
    along = dy*math.cos(angle) + dx*math.sin(angle)
    across = dx*math.cos(angle) - dy*math.sin(angle)
    length = rng.uniform(.12, .26)
    width = rng.uniform(.055, .12)
    bend = across + rng.uniform(.22, .5)*along*along + (warp-.5)*.006
    spacing = rng.uniform(.012, .018)
    ridges = np.clip((np.cos(bend*math.tau/spacing)-.15)/.85, 0, 1)**2
    envelope = (1-smooth(width*.60, width, abs(across))) * (1-smooth(length*.45, length, abs(along)))
    wear = smooth(.26, .70, erosion*.65+meso*.35)
    comb = np.maximum(comb, ridges*envelope*wear*rng.uniform(.045, .12))
for _ in range(19):
    cx, cy = rng.random(2)
    dx, dy = (u-cx+.5)%1-.5, (v-cy+.5)%1-.5
    angle = rng.uniform(-math.pi, math.pi)
    along = dx*math.cos(angle)+dy*math.sin(angle)
    across = -dx*math.sin(angle)+dy*math.cos(angle)
    curve = across + .13*along*along + (warp-.5)*.003
    width = rng.uniform(.0005, .0015)
    length = rng.uniform(.018, .10)
    stroke = np.exp(-(curve/width)**2) * (1-smooth(length*.45, length, abs(along)))
    scratches = np.maximum(scratches, stroke*smooth(.20, .55, erosion)*rng.uniform(.025, .075))
height = np.clip(core*(1-skim)+skim_height*skim+comb*(.35+.65*skim)-scratches, .08, .94)
# Fine dust and mineral colour differences are restrained. Occlusion belongs to
# its own channel, rather than black outlines painted into BaseColor.
core_rgb = np.array([133, 127, 114], dtype=np.float32)
skim_rgb = np.array([155, 150, 136], dtype=np.float32)
color = core_rgb[None, None, :]*(1-skim[..., None])+skim_rgb[None, None, :]*skim[..., None]
color += ((meso-.5)*9+(grain-.5)*7+(macro-.5)*4)[..., None]
color += aggregate[..., None]*np.array([6, 5, 3], dtype=np.float32)
rough = np.clip(.88*(1-skim)+.76*skim+(grain-.5)*.065+pores*.055+scratches*.6, .67, .98)
cavity = np.maximum(0, gaussian_filter(height, 4, mode='wrap')-height)
ao = np.clip(1-cavity*1.0-pores*.12, .72, 1)
dx = (np.roll(height, -1, 1)-np.roll(height, 1, 1))*.5
dy = (np.roll(height, -1, 0)-np.roll(height, 1, 0))*.5
strength = CFG['relief_depth_cm']*N/CFG['tile_size_cm']
normal = np.stack((-dx*strength, dy*strength, np.ones_like(height)), axis=-1)
normal /= np.linalg.norm(normal, axis=-1, keepdims=True)

maps = {
    'BaseColor': np.uint8(np.clip(color, 0, 255)),
    'Normal': np.uint8(np.clip(normal*.5+.5, 0, 1)*255),
    'Surface': np.uint8(np.stack((rough, ao, skim), axis=-1)*255),
    'Height': np.uint16(height*65535),
}
manifest = dict(config=CFG, channels={}, provenance='Project-authored procedural mineral surface; no third-party imagery',
                height_convention='white=raised; physical range 0.65 cm; OpenGL normal, flip green on UE import',
                packed_surface='R=roughness, G=ambient occlusion, B=compressed adhesive coverage')
for channel, data in maps.items():
    path = OUT/('MortarRelief_'+channel+'.png')
    Image.fromarray(data).save(path)
    manifest['channels'][channel] = str(path)
(ROOT/'Authored/material-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('Authored mortar relief PBR: BaseColor, Normal, packed surface and 16-bit height')
