"""Place palm rub, edge wear and joinery dust on the cut garments in rest space."""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter


def _grain_mask():
    # A separate sample breaks the broad deposition field into wood flour and larger flecks.
    rng = np.random.default_rng(71126)
    size = (512, 512)
    random = rng.random(size)
    specks = np.maximum(random - .93, 0) / .07
    flour = gaussian_filter(rng.standard_normal(size), 3.5, mode='wrap')
    flour = np.clip(.22 + flour * 1.3, .02, .55)
    fibres = gaussian_filter(specks ** 8, (.65, 2.2), mode='wrap')
    values = np.clip(flour + 2.0 * fibres + .59 * specks ** 4, 0, 1)
    out = Path(__file__).resolve().parents[3] / 'SourceAssets/VillageCarpenterNPC/Outfit/Detail'
    out.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.rint(values * 255).astype('uint8')).convert('RGB').save(out / 'T_Carpenter_Wear_Mask.png')


def _band(distance, width):
    return np.exp(-.5 * (distance / width) ** 2)


def _smooth(low, high, value):
    t = np.clip((value - low) / (high - low), 0, 1)
    return t * t * (3 - 2 * t)


def bake_wear(mesh):
    points = np.asarray(mesh['positions'])
    fields = np.zeros((len(points), 2))
    for name, (a, _, b, _) in mesh['parts'].items():
        x, y, z = points[a:b].T
        side = np.abs(x)
        front = _smooth(-1, 7, y)
        label = name.lower()
        if label == 'trousers':
            knee = _band(z - np.where(x > 0, 53., 55.), 6.8) * front
            seat = _band(z - 90., 9.) * _smooth(3, 12, -y)
            hem = _band(z - 21., 5.5)
            rub = knee * np.where(x > 0, .70, .45) + .22 * seat + .18 * hem
            dust = knee * np.where(x > 0, .55, .31) + .26 * hem
        elif label == 'boots':
            toe = _smooth(7, 19, y) * _band(z - 4., 3.7)
            heel = _smooth(0, 6, -y) * _band(z - 6., 4.2)
            sole_edge = _band(z - .9, 2.)
            rub = .77 * toe + .45 * heel + .31 * sole_edge
            dust = .50 * toe + .47 * sole_edge + .12 * heel
        elif 'skirt' in label or 'apron hem' in label:
            # The right hand brushes down the apron from the waist, leaving one oblique wipe.
            wipe = _band(x - (.34 * (z - 87.) + 7.5), 3.9) * _band(z - 87., 10.)
            hem = _band(z - (68. + side * .19), 2.6)
            rub = .57 * wipe + .46 * hem
            dust = .70 * wipe + .30 * hem
        elif any(word in label for word in ('pocket', 'pouch', 'bartack', 'bar tack')):
            lip = _band(z - np.max(z), 1.65)
            base = _band(z - np.min(z), 1.25)
            rub = .18 + .48 * lip + .20 * base
            dust = .08 + .52 * lip
        elif 'belt' in label:
            edges = np.maximum(_band(z - np.max(z), .46), _band(z - np.min(z), .46))
            rub = .14 + .48 * edges + .19 * front
            dust = .14 * front
        elif 'buckle' in label:
            rub = .20 + .55 * _smooth(1, 4, side)
            dust = 0.
        elif 'collar' in label:
            rub = .14 + .30 * _band(z - 150., 2.0) + .16 * front
            dust = .06 * front
        elif 'sleeve' in label or 'cuff' in label:
            outer = _smooth(27, 37, side)
            rub = .16 + .44 * outer
            dust = .09 + .32 * outer
        elif 'shirt' in label or 'placket' in label or 'shoulder' in label:
            elbow = _smooth(21, 34, side) * _band(z - 124., 6.7)
            rub = .38 * elbow + .09 * front
            dust = .31 * elbow + .16 * front * _band(z - 127., 7.) * _band(x - 7., 7.)
        else:
            continue
        fields[a:b, 0] = np.clip(rub, 0., 1.)
        fields[a:b, 1] = np.clip(dust, 0., 1.)
    mesh['wear_uv'] = fields.round(5).tolist()
    _grain_mask()
