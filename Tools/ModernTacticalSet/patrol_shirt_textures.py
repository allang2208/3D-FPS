"""Bake physical-scale jersey, ripstop and notions for the coyote shirt."""
import hashlib
import json

import numpy as np
from PIL import Image

from field_pants_textures import noise, paired_yarn, yarn
from patrol_shirt_materials import ROOT, SURFACES, TILE_CM


def bake(kind, seed):
    colour, target_roughness, _, n = SURFACES[kind]
    rng = np.random.default_rng(seed)
    y,x = (np.indices((n,n),dtype=np.float32)+.5)/n
    fuzz = noise(rng,n,.72)
    dye = noise(rng,n,n/280)
    broad = noise(rng,n,n/36)
    tau = 2*np.pi
    tone = .010*fuzz+.013*dye+.012*broad
    rough = target_roughness+.014*dye+.008*broad
    metal = np.zeros_like(x)

    if kind == "Jersey":
        # Offset rows of knitted loops form shallow V-shaped wales down the body.
        # A narrow trough at each loop remains visible between the two strands.
        row = y*114+.045*broad
        col = x*136+.035*dye
        wave = .5-.5*np.cos(tau*row)
        left = .5+.5*np.cos(tau*(col+.19*wave))
        right = .5+.5*np.cos(tau*(col-.19*wave-.46))
        loops = np.maximum(left**2, right**2)*(.77+.23*wave)
        height = .0085*loops+.0009*fuzz
        tone += .132*(loops-.55)
        rough += .022*(1-loops)
        ao = .966+.033*loops
    elif kind in ("Ripstop","Reinforcement"):
        warp, weft = x*164+.037*dye, y*152+.029*broad
        cloth = yarn(warp,weft)
        bars = np.maximum(paired_yarn(x+.00028*dye,16),paired_yarn(y+.00025*broad,16))
        if kind == "Ripstop":
            height = .009*cloth+.005*bars+.0008*fuzz
            tone += .128*(cloth-.5)+.026*bars
            rough -= .012*bars
        else:
            # Dense reinforcement at the elbow uses a diagonal float over weave.
            twill = .5+.5*np.cos(tau*(warp-weft)/2)
            height = .006*cloth+.009*twill+.004*bars+.0008*fuzz
            tone += .082*(twill-.5)+.060*(cloth-.5)+.022*bars
        ao = .955+.041*cloth-.006*bars
    elif kind == "Loop":
        # Fuzzy loop pile, with short curved loops in alternating columns.
        u = x*80+.085*dye
        v = y*92+.13*np.sin(tau*u)+.07*broad
        loop = .5+.5*np.cos(tau*(u+.21*np.cos(tau*v)))
        crown = loop**2*(.56+.44*np.cos(tau*v)**2)
        height = .022*crown+.0028*dye+.0016*fuzz
        tone += .21*(crown-.32)+.028*dye
        ao = .89+.102*crown
    elif kind in ("Binding","Thread"):
        if kind == "Binding":
            structure = .73*yarn(x*112,y*80)+.27*(.5+.5*np.cos(tau*x*56))
        else:
            structure = .5+.5*np.cos(tau*(x*50+y*24)+.12*dye)
        height = .013*structure+.001*fuzz
        tone += .15*(structure-.5)
        ao = .953+.046*structure
    else:
        height = .0009*dye+.00065*fuzz
        metal[:] = .20
        rough += .026*dye
        ao = np.full_like(x,.995)

    dx = (np.roll(height,-1,1)-np.roll(height,1,1))*n/(2*TILE_CM)
    dy = (np.roll(height,-1,0)-np.roll(height,1,0))*n/(2*TILE_CM)
    normal = np.stack((-dx,dy,np.ones_like(dx)),2)
    normal /= np.linalg.norm(normal,axis=2,keepdims=True)
    base = np.asarray(colour,dtype=np.float32)*(1+tone[...,None])
    return dict(BaseColor=base, NormalGL=(normal+1)*127.5,
                ORM=255*np.stack((ao,np.clip(rough,.05,.99),metal),2))


def main():
    folder = ROOT/"Textures"
    folder.mkdir(parents=True,exist_ok=True)
    result = {}
    for index,(kind,(colour,rough,sheen,size)) in enumerate(SURFACES.items()):
        maps = {}
        for channel,values in bake(kind,181132+index*59).items():
            path = folder/f"PS_{kind}_{channel}.png"
            Image.fromarray(np.uint8(np.clip(np.rint(values),0,255))).save(path,compress_level=4)
            maps[channel] = hashlib.sha256(path.read_bytes()).hexdigest()
        result[kind] = dict(resolution=size,tile_cm=TILE_CM,base_srgb=colour,roughness=rough,
                            specular=.29,sheen=sheen,sha256=maps)
    (ROOT/"surfaces.json").write_text(json.dumps(result,indent=2),encoding="utf8")


if __name__ == "__main__":
    main()
