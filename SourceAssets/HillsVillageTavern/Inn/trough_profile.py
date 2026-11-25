"""West crib runoff, in cm from its outside end. Image top follows local -Y."""
from pathlib import Path

# The last station reaches the low grass just outside the hitch rail.
STATIONS = [(6, 1, 12), (-18, 4, 8), (-46, 1, 6), (-73, -6, 8),
            (-103, -11, 7), (-133, -12, 9), (-158, -17, 12), (-180, -21, 15)]
BOUNDS = (-207, 32, -57, 40)
MASK_NAME = 'InnTroughRunoff.png'


def bake():
    import numpy as np
    from PIL import Image
    from scipy.interpolate import PchipInterpolator
    from scipy.ndimage import gaussian_filter

    width, height = 512, 256
    x0, x1, y0, y1 = BOUNDS
    dx, dy = (x1-x0)/width, (y1-y0)/height
    x = x0 + (np.arange(width)[None, :] + .5)*dx
    y = y0 + (np.arange(height)[:, None] + .5)*dy
    station, lateral, breadth = np.array(STATIONS).T
    down = -station
    t = np.clip((-x-down[0])/(down[-1]-down[0]), 0, 1)
    s = np.clip(-x, down[0], down[-1])
    rng = np.random.default_rng(73101)

    def grain(scale):
        field = gaussian_filter(rng.standard_normal((height,width)), scale)
        return np.clip(field/field.std(), -2.6, 2.6)

    coarse, fine = grain(8), grain(1.8)
    axis = PchipInterpolator(down, lateral)(s)
    half = PchipInterpolator(down, breadth)(s)
    ends = x + s
    across = y-axis + .95*coarse + .35*fine
    radius = np.hypot(across/half, ends/(half*1.12))
    # Damp soil collects under the end board, then breaks into a sandy fan.
    thread = np.exp(-1.7*radius**2)
    source = np.exp(-((x-1)/13)**2-((y-1)/10)**2)
    fan = np.exp(-((x+166)/24)**2-((y+22+.14*(x+166)+1.4*coarse)/12)**2)
    toe = np.exp(-((x+174)/14)**2-((y+11+.12*(x+174))/5)**2)
    wet = np.clip((1-t)**.8*(.23+.78*thread)+.29*source+.035*coarse,0,1)
    cover = np.clip(.84*thread+.42*source+.53*fan+.38*toe,0,.93)
    cover *= np.clip(.90+.09*coarse+.12*fine*t,.34,1)
    border = np.minimum(np.minimum(x-x0,x1-x),np.minimum(y-y0,y1-y))
    cover *= np.clip(border/5,0,1)
    # Tangent-space slopes encode the shallow bed and the broken lip in cm.
    bed = -1.25*(1-.75*t)*np.exp(-2.7*radius**2)
    lip = .40*np.exp(-((radius-.98)/.31)**2)*(1-.7*t)
    sy,sx = np.gradient(gaussian_filter(bed+lip,1.4),dy,dx)
    nx,ny = -sx,-sy
    packed = np.stack([cover,wet,.5+.5*nx,.5+.5*ny],axis=-1)
    image = Image.fromarray(np.rint(np.clip(packed,0,1)*255).astype('uint8'))
    image.save(Path(__file__).with_name(MASK_NAME))


if __name__ == '__main__':
    bake()
