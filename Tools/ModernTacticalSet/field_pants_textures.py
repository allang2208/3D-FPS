"""Generate repeatable yarn, ripstop, knit and coated hardware PBR tiles."""
import hashlib
import json
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

from field_pants_materials import ROOT,SURFACES,TILE_CM


def noise(rng,n,sigma):
    v=gaussian_filter(rng.standard_normal((n,n),dtype=np.float32),sigma,mode="wrap")
    return np.clip((v-v.mean())/(v.std()+1.e-6),-3.,3.)


def yarn(u,v):
    # Alternating warp and weft floats with rounded shoulders. Both axes
    # meet at even yarn counts on the tile boundary.
    phase=np.cos(np.pi*u)*np.cos(np.pi*v)
    blend=.5+.44*np.tanh(3.25*phase)
    axial=.5+.5*np.cos(2*np.pi*u)
    cross=.5+.5*np.cos(2*np.pi*v)
    return blend*axial+(1.-blend)*cross


def paired_yarn(axis,frequency):
    p=(axis*frequency+.5)%1.-.5
    return np.exp(-((p-.034)/.035)**2)+np.exp(-((p+.034)/.035)**2)


def surface(kind,seed):
    colour,rough,_,n=SURFACES[kind]
    rng=np.random.default_rng(seed)
    y,x=(np.indices((n,n),dtype=np.float32)+.5)/n
    fine=noise(rng,n,.65); dye=noise(rng,n,max(2,n/265)); slow=noise(rng,n,n/35)
    albedo=.013*dye+.012*slow+.012*fine
    roughness=rough+.014*dye
    metallic=np.zeros_like(x)
    if kind=="Ripstop":
        # Reinforcing paired yarns cross a fine, slightly irregular plain
        # weave at 5 mm intervals. Use dye and normal differences together.
        u=x*200+.030*dye;v=y*176+.027*slow
        cloth=yarn(u,v)
        gridx=paired_yarn(x+.00035*slow,16)
        gridy=paired_yarn(y+.00024*dye,16)
        grid=np.maximum(gridx,gridy)+.18*np.minimum(gridx,gridy)
        relief=.0063*cloth+.0105*grid+.0010*fine
        albedo+=.096*(cloth-.5)+.056*grid
        roughness+=.017*(1.-cloth)-.029*grid
        occlusion=.968+.030*cloth-.022*(1.-cloth)*grid
    elif kind=="Stretch":
        # Low rib structure with small knit loops at each course. The rear
        # knee and gusset have finer, darker fibres than the face fabric.
        course=y*112+.042*slow;wale=x*150+.22*np.cos(course*2*np.pi)
        rib=.5+.5*np.cos(2*np.pi*wale)
        loop=.5+.5*np.cos(2*np.pi*course+.9*np.sin(2*np.pi*wale))
        knit=rib*.68+loop*.32
        relief=.010*knit+.0008*fine
        albedo+=.12*(knit-.5);roughness+=.022*(1.-knit)
        occlusion=.954+.043*knit
    elif kind=="Reinforcement":
        # Tightly packed twill with staggered warp floats and subdued nap.
        u=x*142+.032*dye;v=y*138+.026*slow
        twill=.5+.5*np.cos(2*np.pi*(u-v)/2)
        woven=.36*yarn(u,v)+.64*twill
        nap=noise(rng,n,(.95,n/450))
        relief=.0095*woven+.0016*nap
        albedo+=.083*(woven-.5)+.025*nap
        occlusion=.962+.036*woven
    elif kind in ("Webbing","Thread"):
        if kind=="Webbing":
            warp=x*92;weft=y*76
            weave=yarn(warp,weft)
            structure=.7*weave+.3*(.5+.5*np.cos(2*np.pi*(x*46)))
        else:
            structure=.5+.5*np.cos(2*np.pi*(x*48+y*22)+.11*slow)
        relief=.014*structure+.001*fine
        albedo+=.135*(structure-.5)
        roughness+=.019*(1.-structure)
        occlusion=.947+.050*structure
    else:
        # Matte coated small zip furniture. Speckle stays within the coating.
        relief=.0006*fine+.00075*dye
        albedo=.012*slow+.018*fine
        roughness+=.027*fine
        metallic[:]=.13
        occlusion=np.ones_like(x)*.99
    colour=np.asarray(colour,dtype=np.float32)[None,None,:]*(1.+albedo[:,:,None])
    dx=(np.roll(relief,-1,1)-np.roll(relief,1,1))*n/(2.*TILE_CM)
    dy=(np.roll(relief,-1,0)-np.roll(relief,1,0))*n/(2.*TILE_CM)
    normal=np.stack((-dx,dy,np.ones_like(dx)),axis=2)
    normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    orm=np.stack((occlusion,np.clip(roughness,.05,.99),metallic),axis=2)
    return {"BaseColor":colour,"NormalGL":(normal*.5+.5)*255.,"ORM":orm*255.}


def main():
    folder=ROOT/"Textures";folder.mkdir(parents=True,exist_ok=True)
    report={}
    for i,(kind,(colour,rough,sheen,n)) in enumerate(SURFACES.items()):
        checksums={}
        for channel,values in surface(kind,181126+i*41).items():
            file=folder/f"FT_{kind}_{channel}.png"
            Image.fromarray(np.uint8(np.clip(np.rint(values),0,255))).save(file,compress_level=4)
            checksums[channel]=hashlib.sha256(file.read_bytes()).hexdigest()
        report[kind]=dict(resolution=n,tile_cm=TILE_CM,roughness=rough,specular=.29,
                          sheen=sheen,base_srgb=colour,sha256=checksums)
    (ROOT/"surfaces.json").write_text(json.dumps(report,indent=2),encoding="utf8")


if __name__=="__main__":
    main()
