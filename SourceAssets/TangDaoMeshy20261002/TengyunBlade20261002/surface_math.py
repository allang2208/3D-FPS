"""Physical surface recipe shared by mesh authoring and PBR map baking."""
from pathlib import Path
import numpy as np
P = Path(__file__).resolve().parent
FILE = P / 'Textures/Tengyun_GildedDragon_Ornament.png'
try:
    import bpy
    image = bpy.data.images.load(str(FILE), check_existing=True)
    image.colorspace_settings.name = 'Non-Color'
    pixels = np.empty(image.size[0] * image.size[1] * 4, np.float32)
    image.pixels.foreach_get(pixels)
    ART = pixels.reshape(image.size[1], image.size[0], 4)[::-1].copy()
except ImportError:
    from PIL import Image
    with Image.open(FILE) as image:
        ART = np.array(image.convert('RGBA'), np.float32) / 255.
rows, columns = np.nonzero(ART[..., 3] > .15)
X0, X1, Y0, Y1 = columns.min(), columns.max(), rows.min(), rows.max()

def smooth(a, b, q):
    t = np.clip((q-a)/(b-a), 0, 1)
    return t*t*(3-2*t)

def ornament(t, z):
    t, z = np.broadcast_arrays(t, z)
    a, b = (z-.115)/.535, (t-.285)/.47
    visible = (a >= 0) & (a <= 1) & (b >= 0) & (b <= 1)
    x = X0 + (1-np.clip(a, 0, 1))*(X1-X0)
    y = Y0 + (1-np.clip(b, 0, 1))*(Y1-Y0)
    ix, iy = x.astype(np.int32), y.astype(np.int32)
    jx, jy = np.minimum(ix+1, ART.shape[1]-1), np.minimum(iy+1, ART.shape[0]-1)
    fx, fy = (x-ix)[..., None], (y-iy)[..., None]
    rgba = (ART[iy, ix]*(1-fx)+ART[iy, jx]*fx)*(1-fy)+(ART[jy, ix]*(1-fx)+ART[jy, jx]*fx)*fy
    mask = rgba[..., 3] * visible * smooth(.115, .13, z)*(1-smooth(.635, .65, z))
    return mask, rgba[..., :3]

def relief(t, z):
    mask, color = ornament(t, z)
    value = color[..., 0]*.2126+color[..., 1]*.7152+color[..., 2]*.0722
    return mask*(.00013+.000065*value)

def steel_height(t, z):
    x = t*.066
    wave = x*1420+z*15+1.15*np.sin(z*24+x*41)+.42*np.sin(z*71-x*87)
    forged = 2.8e-6*np.sin(wave*np.pi*2)+1.2e-6*np.sin(wave*2.13*np.pi*2)
    grind = .45e-6*np.sin(x*np.pi*2/.00022+.55*np.sin(z*84))
    # Cloud-shaped fine etching, separate from the more prominent dragon inlay.
    clouds = .8e-6*np.sin(x*340+2.8*np.sin(z*19)+.6*np.sin(z*73))
    return forged+grind+clouds

def total_height(t, z):
    return steel_height(t, z)+relief(t, z)
