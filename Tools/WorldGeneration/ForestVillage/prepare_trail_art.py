"""Extract moss islands from the root scan and build one inexpensive grass silhouette mesh."""
import json,sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import gaussian_filter

def separate_moss(scan,out):
    color=np.array(Image.open(next(scan.glob('*_2K_BaseColor.*'))).convert('RGB'))
    hsv=cv2.cvtColor(color,cv2.COLOR_RGB2HSV).astype('f4')
    h,s,v=hsv.transpose(2,0,1)
    moss=np.clip((h-18)/9.,0,1)*np.clip((82-h)/12.,0,1)*np.clip((s-28)/46.,0,1)
    packed=Image.open(next(scan.glob('*_2K_ORM.*'))).convert('RGB')
    packed.putalpha(Image.open(next(scan.glob('*_2K_Displacement.*'))).convert('L'))
    packed.save(out/'T_TrailSoilData.png')
    clean=hsv.copy()
    clean[...,0]=h+(14.-h)*np.clip(moss*1.55,0,1)
    clean[...,1]=s+(np.clip(s*.8,68,150)-s)*moss
    Image.fromarray(cv2.cvtColor(clean.astype('u1'),cv2.COLOR_HSV2RGB)).save(out/'T_TrailSoil.png')
    # Take eight different silhouettes from the original colour scan, with a feathered transparent perimeter.
    score=gaussian_filter(moss,35)
    atlas=Image.new('RGBA',(512,256))
    for i in range(8):
        margin=116
        y,x=np.unravel_index(np.argmax(score[margin:-margin,margin:-margin]),score[margin:-margin,margin:-margin].shape)
        y+=margin;x+=margin
        radius=[78,100,69,96,87,78,103,90][i]
        cut=np.s_[y-radius:y+radius,x-radius:x+radius]
        py,px=np.mgrid[-1:1:complex(2*radius),-1:1:complex(2*radius)]
        alpha=moss[cut]*np.clip((1-np.hypot(px,py))/.28,0,1)
        rgba=Image.fromarray(np.dstack([color[cut],(255*alpha).astype('u1')]))
        atlas.paste(rgba.resize((128,128),Image.Resampling.LANCZOS),((i%4)*128,(i//4)*128))
        score[max(0,y-190):y+191,max(0,x-190):x+191]=0
    atlas.save(out/'T_TrailMossIslands.png')

def patch(out,grass):
    rng=np.random.default_rng(9182)
    blade=np.array(Image.open(grass).convert('RGBA'))
    palette=blade[blade[...,3]>180][:,:3]
    palette=palette[(palette.max(1)>75)&(palette.min(1)>16)]
    W,H=512,128
    im=Image.new('RGBA',(W,H),tuple(np.median(palette,axis=0).astype(int))+(0,))
    draw=ImageDraw.Draw(im)
    for i in range(1550):
        x=rng.uniform(-12,W+12);base=H+rng.uniform(-8,12)
        height=(.42+.27*np.sin(x*.048)+.12*np.sin(x*.092+1.1))*H
        height=max(12,height)*rng.uniform(.38,1.25)
        drift=rng.uniform(-11,12)+np.cos(.035*x)*6
        width=rng.uniform(.65,2.35)
        color=tuple(map(int,palette[rng.integers(len(palette))]))
        draw.polygon([(x-width,base),(x+drift*.27-width*.48,base-height*.60),(x+drift,base-height),
                      (x+drift*.27+width*.48,base-height*.60),(x+width,base)],fill=color+(255,))
    # Taper the ends so neighbouring patches do not form upright rectangular edges.
    pixels=np.array(im)
    yy,xx=np.mgrid[:H,:W]
    edge=np.clip(np.minimum(xx,W-1-xx)/42,0,1)
    pixels[...,3]=(pixels[...,3]*np.clip((yy/H-(1-edge)*.86)*20,0,1)).astype('u1')
    Image.fromarray(pixels).save(out/'T_FarMeadowBand.png')
    pos=[];uv=[];norm=[];ind=[]
    for a in [0.,np.pi*.51]:
        c,s=np.cos(a),np.sin(a)
        start=len(pos)
        for j,(v,off) in enumerate([(-2.35,-.11),(0.,.14),(2.35,-.12)]):
            for k,ht in enumerate([0.,.48]):
                pos.append([v*c-off*s,ht,v*s+off*c]);norm.append([-s,0.,c]);uv.append([j*.5,1.-k])
        for i in [0,2]:
            ind.extend(start+np.array([i,i+2,i+1,i+1,i+2,i+3]))
    arrays=[np.array(v,dtype=d) for v,d in [(pos,'<f4'),(norm,'<f4'),(uv,'<f4'),(ind,'<u2')]]
    raw=b'';views=[];acc=[]
    for i,ar in enumerate(arrays):
        data=ar.tobytes();views.append(dict(buffer=0,byteOffset=len(raw),byteLength=len(data)))
        raw+=data
        entry=dict(bufferView=i,componentType=5123 if i==3 else 5126,count=len(ar),type=['VEC3','VEC3','VEC2','SCALAR'][i])
        if i==0:entry.update(min=ar.min(0).tolist(),max=ar.max(0).tolist())
        acc.append(entry)
    name='SM_ForestMeadowRibbon'
    (out/(name+'.bin')).write_bytes(raw)
    gltf=dict(asset=dict(version='2.0'),scene=0,scenes=[dict(nodes=[0])],nodes=[dict(mesh=0,name=name)],
              meshes=[dict(name=name,primitives=[dict(attributes=dict(POSITION=0,NORMAL=1,TEXCOORD_0=2),indices=3)])],
              buffers=[dict(uri=name+'.bin',byteLength=len(raw))],bufferViews=views,accessors=acc)
    (out/(name+'.gltf')).write_text(json.dumps(gltf))

if __name__=='__main__':
    root,out=map(Path,sys.argv[1:])
    separate_moss(root/'MagnetVFX/Fab/NordicForestGroundRootsCoarse',out)
    patch(out,root/'HillsGrassDistance-R15/T_HillsFarGrass.png')
