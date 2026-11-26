"""Tileable first-person surface maps for the workshop sign and entrance hoist."""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

OUT = Path(__file__).resolve().parent / "Frontage" / "Textures"
SIZE = 512


def make_maps():
    OUT.mkdir(parents=True,exist_ok=True)
    rng = np.random.default_rng(27411)
    y,x = np.mgrid[:SIZE,:SIZE] / SIZE

    def noise(sigma):
        n = gaussian_filter(rng.normal(size=(SIZE,SIZE)),sigma,mode="wrap")
        return n / max(n.std(),1e-8)

    def save(slot, color, height, rough, metal, strength):
        def image(name, values):
            pixels = np.rint(np.clip(values,0,1)*255).astype(np.uint8)
            Image.fromarray(pixels).save(OUT/f"{slot}_{name}.png")
        dx = (np.roll(height,-1,1)-np.roll(height,1,1))*.5*strength
        dy = (np.roll(height,-1,0)-np.roll(height,1,0))*.5*strength
        length = np.sqrt(1+dx*dx+dy*dy)
        image("base_color",color/255)
        image("normal",np.stack((-dx/length,dy/length,1/length),axis=-1)*.5+.5)
        image("roughness",rough)
        image("metallic",np.broadcast_to(metal,(SIZE,SIZE)))

    # The member's UV V axis runs with the fibres. Pores and rays continue around each chamfer.
    fine = noise((5,.7))
    drift = noise((40,15))
    rings = np.sin(2*np.pi*(x*17+.21*drift+.28*np.sin(2*np.pi*(3*x+y))))
    pores = np.maximum(0,fine-.60)
    grain = .40*rings+.19*noise((14,1.8))-.55*pores
    save("SignOak",np.array([92,59,36])+grain[:,:,None]*[21,16,11]+drift[:,:,None]*2.5,
         grain,.56+.06*rings+.045*pores,0,.9)

    # Hammer depressions remain broad compared with the small pits in the black oxide.
    hammer = noise(6)
    pits = np.maximum(0,noise(1.1)-1.15)
    oxide = np.clip(.30+.16*noise(14)+.17*pits,0,.78)
    iron = np.array([91,88,82])*(1-oxide[:,:,None])+np.array([51,45,37])*oxide[:,:,None]
    save("ForgedStrap",iron+hammer[:,:,None]*5,.64*hammer-pits,
         .43+.32*oxide+.038*noise(2),.87-.49*oxide,1.12)

    tarnish = np.clip((noise(16)+.40*noise(3)-.10)*.52,0,.88)
    gold = np.array([171,126,67])*(1-tarnish[:,:,None])+np.array([64,77,61])*tarnish[:,:,None]
    tool = .18*noise((.8,6))+.19*noise(2)
    save("WheelBrass",gold+tool[:,:,None]*7,tool-.32*tarnish,
         .31+.34*tarnish+.024*noise(1),.90-.64*tarnish,.9)

    # A full circumference carries three laid strands; finer yarn twists cross their crowns.
    lay = np.cos(2*np.pi*(3*x-2*y))
    fibre = np.cos(2*np.pi*(21*x+9*y+.10*lay))
    nap = noise((1.3,.65))
    hemp = .53*lay+.20*fibre+.13*nap
    save("HempCord",np.array([145,111,70])+hemp[:,:,None]*[39,33,23],hemp,
         .81-.04*lay+.035*nap,0,4.0)


if __name__=="__main__":
    make_maps()
