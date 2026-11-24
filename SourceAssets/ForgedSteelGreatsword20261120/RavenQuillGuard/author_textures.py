"""Build the steel finish from the resting concept's hammer marks, in registered UV space."""
from pathlib import Path
import json
import cv2
import numpy as np
from PIL import Image
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import minimum_filter
from relief_profile import ATLAS_W, ATLAS_H, CENTER, CREST, FIELD, MEDAL, VANES, PIXELS_PER_CM

HERE = Path(__file__).resolve().parent
ART = HERE / 'Art' / 'ReliefV3'
ART.mkdir(exist_ok=True)
REFERENCE = HERE.parent / 'GuardConcepts20261122/RavenQuill-Effect-V1.png'
rng = np.random.default_rng(221143)

def blur(a, radius):
    return cv2.GaussianBlur(a, (0, 0), radius)

def panel_mask(curves, shape):
    mask = np.zeros(shape, np.uint8)
    for curve in curves:
        keys = np.array(curve)
        span = np.linspace(keys[0,0],keys[-1,0],max(4,int(keys[-1,0]-keys[0,0])))
        top,bot = PchipInterpolator(keys[:,0],keys[:,1:],axis=0)(span).T
        for side in (-1,1):
            x = CENTER + side*span
            contour = np.concatenate((np.stack((x,top),1),np.stack((x[::-1],bot[::-1]),1)))
            cv2.fillPoly(mask,[np.rint(contour).astype(np.int32)],1)
    return mask

def hammer_field(lum, mask):
    # Locate dark parts of individual impressions only on the visible steel lands.
    high = blur(lum,1.5)-blur(lum,6)
    inside = cv2.erode(mask,np.ones((5,5),np.uint8))
    peaks = (high==minimum_filter(high,size=7)) & (inside!=0) & (high < -.013)
    yy,xx = np.where(peaks)
    ordered = sorted(zip(xx,yy),key=lambda p: high[p[1],p[0]])
    occupied = np.zeros_like(mask)
    height = np.zeros_like(lum)
    anchors=[]
    for x,y in ordered:
        if occupied[y,x]: continue
        cv2.circle(occupied,(int(x),int(y)),int(rng.integers(5,9)),1,-1)
        rx,ry = rng.uniform(4.0,9.5),rng.uniform(3.2,6.0)
        angle = rng.uniform(-1.45,1.45)
        depth = float(np.clip(.031-.27*high[y,x],.033,.090))
        anchors.append([int(x),int(y),round(rx,3),round(ry,3),round(angle,3),round(depth,4)])
        radius = int(np.ceil(max(rx,ry)*1.6))
        ys=slice(max(0,y-radius),min(height.shape[0],y+radius+1))
        xs=slice(max(0,x-radius),min(height.shape[1],x+radius+1))
        v,u=np.mgrid[ys,xs]; u=u-x; v=v-y
        a=(u*np.cos(angle)+v*np.sin(angle))/rx
        b=(-u*np.sin(angle)+v*np.cos(angle))/ry
        rr=np.sqrt(a*a+b*b)
        floor=np.maximum(0,1-rr*rr)**1.42
        raised_lip=np.exp(-((rr-.94)/.19)**2)*np.clip(.48+.32*a-.18*b,.12,.95)
        height[ys,xs]+=depth*(-floor+.27*raised_lip)
    # Keep the perimeter planished and preserve the tip profile.
    fade = np.clip(cv2.distanceTransform(mask,cv2.DIST_L2,5)/4,0,1)
    return height*fade,anchors

def registered_plane(src, chart, baseline, finish, slopes):
    (l,t,r,b),(x0,y0,x1,y1)=chart
    yy,xx=np.mgrid[t:b,l:r].astype('f')
    px=x0+(xx-l+.5)*(x1-x0)/(r-l)
    py=y0+(yy-t+.5)*(y1-y0)/(b-t)
    def sample(a):
        return cv2.remap(a,px.astype('f'),py.astype('f'),cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
    oxide,patina,meso,residual=map(sample,src)
    height=slopes*residual
    return finish_maps(height,oxide,patina,meso,baseline,finish,
                       (r-l)/(x1-x0)*PIXELS_PER_CM,
                       (b-t)/(y1-y0)*PIXELS_PER_CM)

def finish_maps(height,oxide,patina,meso,base,rough,tx,ty):
    shape=height.shape
    speck=rng.normal(0,1,shape).astype('f')
    rub=cv2.GaussianBlur(speck,(15,3),3.3,.45)
    scratches=np.zeros(shape,'f')
    for _ in range(int(np.prod(shape)/820)):
        x=int(rng.integers(shape[1])); y=int(rng.integers(shape[0]))
        length=int(rng.integers(3,23))
        cv2.line(scratches,(x,y),(x+length,y+int(rng.integers(-6,6))),float(rng.uniform(.2,1)),1)
    scratches=blur(scratches,.60)
    height=height+.0013*rub-.0038*scratches
    dy,dx=np.gradient(height)
    normal=np.stack((-dx*tx,dy*ty,np.ones(shape,'f')),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    value=np.clip(1-.34*oxide+.085*patina+.12*meso+.010*speck+.15*scratches,.49,1.30)
    rgb=np.array(base)[None,None,:]*value[...,None]
    rgb[...,0]+=6*patina; rgb[...,2]-=4*patina
    orm=np.stack((.977-.13*oxide,rough+.15*oxide-.075*meso+.015*speck-.14*scratches,
                  .93-.23*oxide+.015*meso),axis=-1)
    return [np.rint(np.clip(a,0,255)).astype('uint8') for a in (rgb,(normal*.5+.5)*255,orm*255)]

def main():
    rgb=np.array(Image.open(REFERENCE).convert('RGB'),dtype='f')[:550,:887]/255
    lum=rgb@np.array([.2126,.7152,.0722],dtype='f')
    wing=panel_mask(VANES,lum.shape)
    emblem=panel_mask([CREST],lum.shape)
    wing[cv2.dilate(emblem,np.ones((3,3),np.uint8))!=0]=0
    relief,stamps=hammer_field(lum,wing)
    macro=blur(relief,1.55)
    np.save(ART/'HammerDepthCm.npy',macro)
    (ART/'hammer-strikes.json').write_text(json.dumps({'reference':REFERENCE.name,'columns':['x_px','y_px','radius_x_px','radius_y_px','angle_rad','depth_cm'],'stamps':stamps},separators=(',',':'))+'\n')
    # Filter out the light rig, outlines and cast shadows. Retain only local-scale variation.
    field=blur(lum,1.05)-blur(lum,5.5)
    drift=blur(rng.normal(size=lum.shape).astype('f'),3.0)*5
    atlas=[np.zeros((ATLAS_H,ATLAS_W,3),np.uint8) for _ in range(3)]
    for chart,mask,base,rough,amount in [(FIELD,wing,(79,91,109),.425,1),(MEDAL,emblem,(103,96,91),.40,0)]:
        d=cv2.distanceTransform(mask,cv2.DIST_L2,5)
        inside=np.clip((d-1.75)/3,0,1)
        fine=np.clip(field,-.13,.13)*inside
        metal=np.clip(-relief/.09,0,1)*amount
        oxide=np.clip(.14+.64*metal-2.0*fine,.04,.92)
        # The mesh carries broad dents. Only their residual and micron-scale marks enter normals.
        residual=(relief-macro)*amount+.032*fine
        src=(oxide,drift+.8*fine,np.clip(4*fine-.20*metal,-.65,.65),residual)
        (l,t,r,b),_=chart
        for arr,patch in zip(atlas,registered_plane(src,chart,base,rough,1)):
            arr[t:b,l:r]=patch
    for idx,(base,rough) in enumerate([((182,175,164),.29),((48,55,65),.55),((106,99,91),.39)]):
        l=(idx+1)*512
        grain=rng.normal(size=(384,512)).astype('f')
        drift=blur(grain,8)*18 + blur(grain,2)*2
        for arr,tile in zip(atlas,finish_maps(grain*.0009,np.clip(.16+.12*drift,0,1),drift,drift*.22,base,rough,54,54)):
            arr[640:,l:l+512]=tile
    for name,arr in zip(('BaseColor','Normal','ORM'),atlas):
        Image.fromarray(arr).save(ART/('T_RavenQuill_'+name+'.png'))
    print(f'Authored {len(stamps)} concept-registered hammer strikes and three {ATLAS_W} x {ATLAS_H} finish maps.')

if __name__=='__main__':
    main()
