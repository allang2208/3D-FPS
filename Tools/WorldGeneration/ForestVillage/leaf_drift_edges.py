"""Cut leaf scan borders into seeded drifts while retaining isolated leaf silhouettes."""
import zlib

import numpy as np
from PIL import Image
from scipy.ndimage import label

from prepare_gate_road_surface import smooth


def drift_alpha(opacity, asset_id):
    alpha = np.asarray(opacity, dtype='f4') / 255.
    y, x = np.indices(alpha.shape, dtype='f4')
    x = (x + .5) / alpha.shape[1] - .5
    y = (y + .5) / alpha.shape[0] - .5
    angle = np.arctan2(y, x)
    rng = np.random.default_rng(zlib.crc32(asset_id.encode('ascii')))
    radius = np.full_like(x, .397)
    # The last transparent ring stays inside the atlas tile at every rotation.
    for count, strength in ((2,.032),(3,.030),(5,.020),(8,.014),(13,.008)):
        radius += strength * np.sin(count*angle + rng.uniform(0., 2.*np.pi))
    gap = np.minimum(radius, .454) - np.hypot(x, y)
    keep = smooth(-.012, .022, gap)
    # Keep or discard small connected leaves as a whole at the ragged boundary.
    # Larger overlapping piles instead thin through the continuous feather above.
    ids, count = label(alpha > .09, structure=np.ones((3, 3), dtype='u1'))
    area = np.bincount(ids.ravel(), minlength=count+1)
    centre_gap = np.bincount(ids.ravel(), weights=gap.ravel(), minlength=count+1) / np.maximum(area, 1)
    near = (area >= 6) & (area <= .0007 * alpha.size)
    near[0] = False
    keep = np.where(near[ids], smooth(-.004,.016,centre_gap)[ids], keep)
    # Enforce a curved transparent gutter even on a long, thin connected blade.
    keep *= 1. - smooth(.465,.48,np.hypot(x,y))
    return Image.fromarray(np.rint(255.*alpha*keep).astype('u1'))


def broken_shoulder_edges(near, x, y):
    # Vary the two sides independently in world metres. Keep the worn road centre clear.
    drift = (.48*np.sin(.46*x+.31*y+.93*np.sin(.21*y))
             + .31*np.cos(.63*y-.27*x) + .14*np.sin(1.51*x+.72*y))
    return smooth(1.25,2.30,near+.57*drift) * (1.-smooth(5.4,7.1,near-drift))
