"""Author four sparse gravity streak masks, packed into one streamed RGBA texture."""
import json
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Authored'
OUT.mkdir(parents=True, exist_ok=True)
W, H = 1024, 1024
y, x = np.mgrid[0:1:complex(H), 0:1:complex(W)].astype(np.float32)

def noise(rng, width, height):
    small = Image.fromarray(rng.integers(0, 256, (height, width), dtype=np.uint8))
    return np.asarray(small.resize((W, H), Image.Resampling.BICUBIC), dtype=np.float32) / 255

def smooth(a, b, value):
    t = np.clip((value - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)

masks = []
for index in range(4):
    rng = np.random.default_rng(924720 + index)
    broad, medium, fine = noise(rng, 11, 17), noise(rng, 55, 87), noise(rng, 220, 300)
    center = rng.uniform(.42, .58)
    warp = (broad - .5) * .035 + (medium - .5) * .006
    # Uneven source patch and a pale absorbed halo; no opaque circular outline.
    source = np.exp(-((x-center+warp)/rng.uniform(.12,.19))**2
                    -((y-.14+(broad-.5)*.07)/.105)**2)
    mask = source * (.17 + .27 * broad)
    for streak in range(8 + index * 2):
        origin = np.clip(center+rng.normal(0,.072), .20, .80)
        top, end = rng.uniform(.07,.19), rng.uniform(.32,.89)
        width = rng.uniform(.004,.019)
        drift = rng.uniform(-.025,.025) * (y-top)
        track = x-origin+warp+drift
        taper = np.maximum(.22, 1-.72*np.clip((y-top)/(end-top),0,1))
        wet = np.exp(-(track/(width*taper))**2)
        halo = np.exp(-(track/(width*3.6*taper))**2)
        falloff = smooth(top-.035, top+.015, y)*(1-smooth(end-.15,end,y))
        broken = .28 + .72*smooth(.16,.75,medium*.65+broad*.35)
        flow = (.74*wet+.17*halo)*falloff*broken*rng.uniform(.38,.85)
        mask = 1-(1-mask)*(1-flow)
    # A few irregular dark colonies around the moist source, never green blobs
    # across the entire wall. Fine breakup leaves the wall surface visible.
    specks = smooth(.60,.84,medium*.7+fine*.3)*source*.18
    mask = (mask+specks)*(.68+.32*fine)
    edge = smooth(.025,.13,x)*(1-smooth(.87,.975,x))*smooth(.015,.075,y)*(1-smooth(.89,.98,y))
    masks.append(np.clip(mask*edge,0,1))
Image.fromarray(np.uint8(np.stack(masks,-1)*255), 'RGBA').save(OUT/'WallStreakMasks.png')
(OUT/'authoring.json').write_text(json.dumps({
    'source':'Project-authored procedural masks; no downloaded images',
    'seed':924720, 'size':[W,H], 'channels':'RGBA = four independent streak families',
    'appearance':'Uneven source patches, tapered interrupted gravity trails, soft absorbed halos',
    'game_tested':False
},indent=2),encoding='utf-8')
print('WALL_STREAK_MASKS_AUTHORED',str(OUT/'WallStreakMasks.png'))
