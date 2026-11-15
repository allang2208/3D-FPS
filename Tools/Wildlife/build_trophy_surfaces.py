"""Generate UV-space colour and normal maps for the wildlife pickup meshes."""
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates

out = Path(__file__).resolve().parents[2] / "SourceAssets/HillsWildlifeLoot"
out.mkdir(parents=True, exist_ok=True)
N = 512
y, x = np.mgrid[0:N, 0:N] / N
coats = {
    "deer_hide": ([66,44,31],[154,114,79],[179,145,105]),
    "boar_hide": ([40,35,32],[102,87,70],[142,124,99]),
    "fox_pelt": ([75,43,29],[181,94,47],[218,188,146]),
    "wolf_pelt": ([50,47,45],[131,125,117],[176,163,140]),
}

for seed, name in enumerate([*coats, "deer_antler", "boar_tusk", "crow_feather"]):
    rng = np.random.default_rng(915 + seed)
    noise = rng.standard_normal((N,N))
    def texture(sigmas):
        a = gaussian_filter(noise, sigmas, mode='wrap')
        return (a-a.mean()) / max(a.std(), .001)
    clouds = texture(18)
    wrinkles = texture(4)
    if name in coats:
        deep, mid, pale = map(np.array,coats[name])
        fibers = texture((7.5, .48))
        sway = .010*np.sin(11*y+8*x) + .006*clouds + .038*(y-.44)*(2*x-1)
        strand = map_coordinates(fibers,[N*y,N*(x+sway)],order=1,mode='wrap')
        flank = np.abs(2*x-1)**1.6
        mix = np.clip(.38 + .42*flank + .08*clouds + .105*strand,0,1)
        rgb = deep+(mid-deep)*mix[:,:,None]
        guard = np.clip((strand-1.1)*.33,0,.54) + .10*flank
        rgb += (pale-rgb)*guard[:,:,None]
        relief = strand*.34 + wrinkles*.12
    elif name=='crow_feather':
        vane = np.sin(2*np.pi*(70*y-23*np.abs(2*x-1)**.74 + .36*wrinkles))
        sheen = .5+.5*np.cos(7*y+3*x)
        tone = (vane*3.8+clouds*1.8+wrinkles*1.4)[:,:,None]
        rgb = np.array([25,27,32])+tone + sheen[:,:,None]*[3,6,10]
        shaft = np.exp(-((x-.5)/.025)**2)
        rgb += shaft[:,:,None]*[15,13,10]
        relief = vane*.25+wrinkles*.025
    else:
        ivory = name=='boar_tusk'
        ridge = texture((11, .75))
        base, tip = ([117,87,63],[223,209,169]) if ivory else ([82,62,43],[168,143,106])
        weight = np.clip((1-y)**.85*.72+.14+.12*clouds+.06*ridge,0,1)
        rgb = np.array(base)+(np.array(tip)-base)*weight[:,:,None]
        pores = np.maximum(0.,-noise-1.45)*np.clip((y-.50)*2.5,0,1)
        rgb -= pores[:,:,None]*(5 if ivory else 13)
        relief = ridge*(.19 if ivory else .45)+wrinkles*.13-pores*.10
    dy,dx=np.gradient(relief)
    normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    Image.fromarray(np.uint8(np.clip(rgb,0,255))).save(out/f"T_{name}_BC.png")
    Image.fromarray(np.uint8(np.clip(127.5*(normal+1),0,255))).save(out/f"T_{name}_N.png")
