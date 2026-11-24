"""PBR surface sheet shared by the Frontier workbench variants. Colours are sRGB."""
from pathlib import Path
import numpy as np
from PIL import Image

DEST = Path(__file__).resolve().parent / 'Textures'
STYLES = [
    ('graphite', (56,64,69), .43, .75), ('steel', (124,134,140), .31, .90),
    ('bronze', (176,125,68), .36, .80), ('cyan', (59,170,170), .39, .42),
    ('recess', (25,28,29), .64, .32), ('mark', (194,197,177), .52, .05),
    ('wax', (146,100,57), .58, 0), ('weave', (67,82,80), .82, 0),
    ('thin', (108,64,43), .46, 0), ('pad', (63,64,58), .71, 0),
    ('thread', (166,151,120), .74, 0), ('fast', (174,116,55), .44, .02),
    ('twist', (90,123,130), .49, .03), ('soft', (140,137,98), .72, 0),
    ('serving', (39,44,45), .55, 0), ('rubber', (47,54,55), .82, 0)]
if __name__ == '__main__':
    DEST.mkdir(exist_ok=True)
    size = 512
    y,x = np.mgrid[:size,:size] / size
    out = {s:np.zeros((size*4,size*4,3),np.uint8) for s in ('Color','Normal','ORM')}
    rng = np.random.default_rng(2252)
    for i,(name,col,rough,metal) in enumerate(STYLES):
        grain = rng.normal(0,1,(size,size))
        width = 32
        coarse = np.asarray(Image.fromarray(rng.integers(0,255,(width,width),dtype=np.uint8)).resize((size,size),Image.Resampling.BICUBIC))/255-.5
        a = np.cos(2*np.pi*(x*31+y*3)); b = np.cos(2*np.pi*(y*43-x*6))
        if name in ('wax','weave','thread','fast','twist','soft','serving'):
            parity = np.cos(2*np.pi*(x*15.5+y*1.5))*np.cos(2*np.pi*(y*21.5-x*3))
            h = (.5+.43*parity)*a + (.5-.43*parity)*b
            shade = .12*h+.075*coarse+.012*grain
        elif name in ('thin','pad','rubber'):
            h = coarse*.95+grain*.10+np.sin(2*np.pi*(x*11+y*12)+coarse*8)*.18
            shade = h*.12+coarse*.07
        else:
            h = np.sin(2*np.pi*y*128 + coarse*.9)*.10 + grain*.09
            shade = h*.12 + .036*coarse
        dy,dx = np.gradient(h)
        normal = np.stack((-dx*.8,dy*.8,np.ones_like(dx)),axis=2)
        normal /= np.linalg.norm(normal,axis=2,keepdims=True)
        pix = {'Color':np.asarray(col)[None,None,:]*(1+shade[:,:,None]),
               'Normal':(normal+.99999)*127.5,
               'ORM':np.stack((.96+np.clip(h,-1,1)*.035,np.clip(rough+.043*h+.04*coarse,0,1),np.full_like(h,metal)),axis=2)*255}
        row,colidx=divmod(i,4)
        for kind,arr in pix.items():
            out[kind][row*size:(row+1)*size,colidx*size:(colidx+1)*size] = np.clip(arr,0,255).astype('uint8')
    for kind,im in out.items(): Image.fromarray(im).save(DEST/f'T_FrontierMods_{kind}.png')
