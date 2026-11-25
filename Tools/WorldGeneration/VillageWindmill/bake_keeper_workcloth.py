"""Bake cut-specific flax linen and brushed twill, including their sewn finish."""
import cv2
import numpy as np
from PIL import Image
from keeper_workcloth import SOURCE, texture_name


def make(panel):
    apron=panel=="Apron"
    w,h=(1024,2048) if apron else (2048,1024)
    rng=np.random.default_rng(241 if apron else 386)
    x,y=np.meshgrid((np.arange(w,dtype="f")+.5)/w,(np.arange(h,dtype="f")+.5)/h)

    def field(cols,rows):
        # Extra wrapped columns provide continuity across the rear skirt seam.
        g=rng.uniform(-1,1,(rows+2,cols)).astype("f")
        g=np.pad(g,((0,0),(1,1)),mode="wrap")
        return cv2.resize(g,((cols+2)*max(1,w//cols+1),(rows+2)*max(1,h//rows+1)),interpolation=cv2.INTER_CUBIC)[
            h//rows+1:h//rows+1+h,w//cols+1:w//cols+1+w]

    def strip(d,width):
        return np.exp(-np.square(d/width))

    def dash(phase):
        return np.clip((np.cos(2*np.pi*phase)+.55)*1.35,0.,1.)

    def mix(a,b,t):
        return a+(b-a)*np.clip(t,0,1)[...,None]

    macro=field(11,16) if apron else field(41,16)
    grain=field(52,104) if apron else field(148,82)
    fx,fy=(152,248) if apron else (586,318)
    warp=x*fx+.16*field(29,20)+.09*np.sin(y*24.+x*34.)
    weft=y*fy+.14*field(19,35)+.07*np.sin(x*35.-y*21.)
    a=np.cos(2*np.pi*warp)
    b=np.cos(2*np.pi*weft)
    over=np.cos(np.pi*(warp+weft)) if apron else np.cos(2*np.pi*(warp-weft)/4.)
    yarn=.26*(a+b)+.31*over*(a-b)
    slubs=.63*field(171 if apron else 385,17)+.37*field(17,204 if apron else 115)
    noise=rng.normal(0,1,x.shape).astype("f")
    base=np.array([182,165,134] if apron else [110,79,65],dtype="f")
    val=1.+.032*macro+.033*grain+.048*slubs+.085*yarn+.011*noise
    color=base*val[...,None]
    relief=.38*yarn+.11*slubs+.045*noise
    rough=.85+.033*grain+.044*yarn
    if apron:
        # A narrow flax/woad selvedge. Strength follows warp/weft crossings.
        side=np.minimum(x,1.-x)
        blue=(.57*strip(side-.054,.0075)+.64*strip(side-.071,.0034))
        blue+=.59*strip(y-.916,.0045)+.48*strip(y-.928,.0023)
        color=mix(color,color*np.array([.55,.68,.78]),blue*(.86+.14*a))
        hem=strip(side-.023,.0027)+strip(y-.974,.0024)
        thread=strip(side-.028,.0016)*dash(y*114.)+strip(y-.969,.00125)*dash(x*78.)
        # Small broken fibre streaks collect on the work face and raised folds.
        flour=np.clip((field(43,62)*.58+field(9,14)*.46+.34*slubs-.24)*1.7,0,1)
        flour*=np.exp(-((x-.37)/.31)**2-((y-.52)/.29)**2)
        grime=np.clip((.12-y+.078*grain)*4.,0,1)+np.clip((y-.938+.025*grain)*8.,0,1)
        color*=1.-.055*grime[...,None]
        color=mix(color,np.array([221,210,186]),flour*.36)
        # Patch pattern, cut on a slightly different grain, with a doubled mouth.
        t0=.245-.026*np.clip((x-.512)/.35,0.,1.)
        pv=(y-t0)/(.473-t0)
        clip=.036*np.clip((pv-.80)/.20,0.,1.)
        left=x-.512-clip
        right=.862-clip-x
        inside=(left>=0)&(right>=0)&(pv>=0)&(pv<=1)
        edge=np.minimum(left,right)
        lip=strip(pv-.07,.018)
        thread+=inside*(strip(edge-.013,.0020)*dash(y*129.)+
                        strip(pv-.945,.007)*dash(x*90.)+strip(pv-.106,.0060)*dash(x*93.))
        tack=inside*(strip(left-.020,.013)*strip(pv-.079,.037)+strip(right-.020,.013)*strip(pv-.079,.037))
        hem+=inside*(strip(edge-.006,.0033)+strip(pv-.979,.011)+.9*strip(pv-.088,.013))
        patch_val=(.956+.028*slubs+.014*macro+.036*np.cos(2*np.pi*(warp*.91+weft*.06)))
        color*=np.where(inside,patch_val,1.)[...,None]
        color=mix(color,color*np.array([.47,.54,.56]),tack*.78)
        relief+=inside*(.32*lip+.25*tack)
    else:
        # Six gores with a gently bowed seam; a brushed darker facing at the foot.
        phase=6.*(x+.011*np.sin(2*np.pi*x+1.3)*(y-.15)**2)+.49
        phased=phase-np.rint(phase)
        seam=strip(phased,.018)
        welt=strip(phased-.020,.010)
        thread=strip(phased-.032,.0075)*dash(y*132.)
        hem=seam+.85*strip(y-.944,.0040)+.75*strip(y-.980,.0025)
        thread+=strip(y-.95,.0015)*dash(x*191.)+.65*strip(y-.975,.0014)*dash(x*191.+.3)
        facing=np.clip((y-.946)/.011,0.,1.)
        color*= (1.-.19*facing+.022*np.sin(np.floor(phase+.5)*4.))[:,:,None]
        raised=strip(y-.912,.0057)+.75*strip(y-.924,.0031)
        color=mix(color,np.array([128,101,80]),raised*.53)
        wear=np.clip((y-.93+.026*grain)*9.,0,1)*np.clip(.6*macro+.4*slubs+.22,0,1)
        color=mix(color,np.array([146,119,94]),wear*.29)
        relief+=.47*welt+.21*raised
    color*=np.clip(1.-.20*hem,.70,1.)[...,None]
    color=mix(color,np.array([213,193,158] if apron else [155,122,94]),thread*.81)
    relief+=.60*thread-.35*hem
    rough=np.clip(rough+.036*hem+.025*thread,.72,.96)
    gy,gx=np.gradient(relief)
    norm=np.stack((-gx*.78,gy*.78,np.ones_like(gx)),axis=-1)
    norm/=np.linalg.norm(norm,axis=2,keepdims=True)
    imgs={"Color":color, "Normal":(norm*.5+.5)*255., "Roughness":rough*255.}
    SOURCE.mkdir(parents=True,exist_ok=True)
    for channel,arr in imgs.items():
        Image.fromarray(np.uint8(np.clip(arr,0,255))).save(SOURCE/(texture_name(panel,channel)+".png"))


if __name__=="__main__":
    make("Apron")
    make("SkirtPanels")
