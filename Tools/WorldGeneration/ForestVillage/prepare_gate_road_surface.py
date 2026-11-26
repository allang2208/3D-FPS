"""Bake a streamable two-look PBR palette and metre-based wear weights for both surveyed roads."""
from pathlib import Path
import sys
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

MUD='8664de27-473d-45da-834d-9d7f8c6facc4'
GRAVEL='c438046e-58fa-412f-92ae-c1c13a61eca8'
ORIGIN=(-480.,224.)
STEP=.625

def smooth(lo,hi,x):
    v=np.clip((x-lo)/(hi-lo),0,1)
    return v*v*(3.-2.*v)

def weights(src,roads):
    y,x=np.indices((256,1024))
    x=ORIGIN[0]+(x+.5)*STEP
    y=ORIGIN[1]+(y+.5)*STEP
    points=np.column_stack((x.ravel(),y.ravel()))
    core=np.zeros_like(x); quarry=np.zeros_like(x); sample=np.zeros_like(x)
    for filename in ('gate-road','quarry-road'):
        line=np.loadtxt(roads/(filename+'.csv'),delimiter=',',skiprows=1)[:,:2]
        if filename=='gate-road':
            line=line[::-1]
        chain=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(line,axis=0),axis=1))]
        d,index=cKDTree(line).query(points)
        d=d.reshape(x.shape);index=index.reshape(x.shape);station=chain[index]
        heading=np.gradient(line,axis=0)
        heading/=np.maximum(np.linalg.norm(heading,axis=1,keepdims=True),.001)
        side=heading[index,0]*(y-line[index,1])-heading[index,1]*(x-line[index,0])
        # Opposite verges have separate widths. Junctions combine by maximum, never by addition.
        width=1.95+.38*np.sin(station*.14+np.sign(side)*1.4)+.22*np.sin(.41*x+.21*y)
        wear=(1-smooth(width-.55,width+1.25,d))*smooth(0,2.,station)
        core=np.maximum(core,wear)
        if filename=='gate-road':
            sample=smooth(9.,11.,station)*(1.-smooth(37.,39.,station))*(1-smooth(4.,5.5,d))
        else:
            quarry=smooth(chain[-1]-75.,chain[-1]-8.,station)*(1.-smooth(4.,7.,d))
    macro=np.clip(.5+.25*np.sin(x*.113+y*.074)+.15*np.sin(y*.29-x*.09)+.10*np.cos(y*.57+x*.25),0,1)
    img=np.stack([core,quarry,sample,macro],axis=-1)
    Image.fromarray(np.rint(img*255).astype('uint8')).save(src/'T_RoadWearField.png')

def channel(path,mode='RGB'):
    with Image.open(path) as img:
        if img.mode in ('I','I;16','I;16B'):
            return Image.fromarray((np.asarray(img,dtype=np.float32)/257.).clip(0,255).astype('uint8')).convert(mode)
        return img.convert(mode)

def fab(folder,uid):
    def one(ch,mode):return channel(next((folder/uid).glob('*_2K_'+ch+'.jpg')),mode)
    height='Displacement' if uid==MUD else 'Bump'
    return one('BaseColor','RGB'),one('Normal','RGB'),Image.merge('RGB',(one('AO','L'),one('Roughness','L'),one(height,'L')))

def normalized_lightness(color,target):
    # Match the village earth reference while retaining differences in grain and mineral colour.
    a=np.asarray(color,dtype=np.float32)
    mean=np.asarray(color.resize((1,1),Image.Resampling.BOX),dtype=float)[0,0]
    gain=np.clip((target+1.)/(mean+1.),.68,1.35)
    return Image.fromarray(np.clip(a*gain,0,255).astype('uint8'))

def palette(src):
    village=src/'Village'
    soil=channel(village/'ChapelEarth_ORM.tga');rock=channel(village/'RockyRoad_RHAOM.tga')
    b=channel(village/'ChapelEarth_B.tga')
    def packed(ao,rough,h):
        return Image.merge('RGB',(ao,rough,h.resize(ao.size,Image.Resampling.BILINEAR)))
    rocky_height=channel(village/'RockyRoad_Height.png','L')
    materials=[fab(src/'Fab',MUD),fab(src/'Fab',GRAVEL),
        (b,channel(village/'ChapelEarth_N.tga'),packed(soil.getchannel('R'),soil.getchannel('G'),channel(village/'ChapelEarth_H.tga','L'))),
        (channel(village/'RockyRoad_Albedo.tga'),channel(village/'RockyRoad_Normal.tga'),packed(rock.getchannel('B'),rock.getchannel('R'),rocky_height))]
    target=np.asarray(b.resize((1,1),Image.Resampling.BOX),dtype=float)[0,0]
    for j,name in enumerate(('Color','Normal','Data')):
        size=2048 if j==0 else 1024
        pad=size//64
        canvas=Image.new('RGB',(2*size,2*size))
        for k,triple in enumerate(materials):
            im=triple[j]
            if j==0 and k!=2:im=normalized_lightness(im,target*(1.06 if k%2 else 1.))
            im=im.resize((size-2*pad,size-2*pad),Image.Resampling.LANCZOS)
            tile=np.pad(np.asarray(im),((pad,pad),(pad,pad),(0,0)),mode='wrap')
            canvas.paste(Image.fromarray(tile),((k%2)*size,(k//2)*size))
        canvas.save(src/('T_RoadPalette'+name+'.png'))

if __name__=='__main__':
    directory,roads=map(Path,sys.argv[1:])
    weights(directory,roads)
    palette(directory)
