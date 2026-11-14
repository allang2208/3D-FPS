from PIL import Image
from pathlib import Path
import numpy as np
r=Path(__file__).resolve().parent
for name in ('Platform','Wall'):
    src='T_CartBayFloorMasks' if name=='Platform' else 'T_CartBayWallMasks'
    image=np.asarray(Image.open(r/(src+'.png')),dtype=np.float32)/255
    a,b,c,d=np.moveaxis(image,2,0)
    if name=='Platform':
        weights=[a*.90,b*.96,c*.70,d*.065]
        colors=[[.020,.018,.015],[.037,.033,.03],[.36,.31,.24],[.245,.227,.202]]
        rough=[.84,.43,.96,.77]
    else:
        weights=[a*.52,b*.64,c*.25]
        colors=[[.09,.076,.060],[.23,.193,.153],[.28,.25,.21]];rough=[.63,.94,.84]
    total=np.maximum(sum(weights),.00001)
    rgb=sum(w[:,:,None]*np.array(col,np.float32) for w,col in zip(weights,colors))/total[:,:,None]
    rgb=np.where(rgb<=.0031308,12.92*rgb,1.055*np.maximum(rgb,0)**(1/2.4)-.055)
    opacity=1-np.prod([1-w for w in weights],axis=0)
    rgba=np.dstack([rgb,opacity]);roughness=sum(w*k for w,k in zip(weights,rough))/total
    # Store in the final projected UV orientation in the atlas.
    def save(arr,filename):
        out=Image.fromarray(np.uint8(np.clip(arr,0,1)*255))
        if name=='Wall':out=out.transpose(Image.Transpose.ROTATE_90)
        out=out.resize((2048,2048),Image.Resampling.LANCZOS)
        out.save(r/(filename+'.png'))
    save(rgba,'T_'+name+'PatinaColor')
    save(roughness,'T_'+name+'PatinaRoughness')
