"""Recover the two approved appliques and their five enamel cells from the original plate.
Pixel coordinates are in the left-hand elevation of the 1536 x 1024 design.
The right-hand close-up supplies the brushed metal and laminated enamel microfinish.
"""
import json
from pathlib import Path

import cv2 as cv
import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter
from shapely import contains_xy
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

src = Path(__file__).resolve().parent
rgb = cv.cvtColor(cv.imread(str(src / 'AuroraReference.png')), cv.COLOR_BGR2RGB)
if rgb.shape != (1024, 1536, 3):
    raise ValueError('Expected the approved Aurora R1 design sheet')
out = src / 'Textures'
out.mkdir(exist_ok=True)
art = rgb[:, :640]
y, x = np.mgrid[:1024, :640]
left = art[:, :12].mean(1)[:, None]
right = art[:, 630:640].mean(1)[:, None]
background = left + (right-left) * (x/635)[:, :, None]
distance = np.max(abs(art-background), axis=2)
candidate = (distance > 24).astype('uint8')
candidate[:151, :245] = 0  # design title
hsv = cv.cvtColor(art, cv.COLOR_RGB2HSV)
enamel = ((hsv[:,:,1]>77) & (hsv[:,:,2]>40) & (hsv[:,:,0]>52) & (hsv[:,:,0]<153)).astype('uint8')
enamel = cv.morphologyEx(enamel, cv.MORPH_CLOSE, cv.getStructuringElement(cv.MORPH_ELLIPSE,(3,3)))
regions = []
region_masks = {}
kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE,(3,3))

def region(name, binary, seed, windows=False):
    curves, hierarchy = cv.findContours(binary.copy(), cv.RETR_CCOMP, cv.CHAIN_APPROX_SIMPLE)
    index = max((i for i,c in enumerate(curves) if hierarchy[0,i,3]<0 and cv.pointPolygonTest(c,seed,False)>=0),
                key=lambda i:cv.contourArea(curves[i]))
    holes = [i for i in range(len(curves)) if windows and hierarchy[0,i,3]==index and cv.contourArea(curves[i])>450]
    rings = [cv.approxPolyDP(curves[i], .73, True)[:,0,:].tolist() for i in [index,*holes]]
    poly = Polygon(rings[0],rings[1:]).buffer(0)
    if poly.geom_type!='Polygon':
        poly=max(poly.geoms,key=lambda q:q.area)
    poly=orient(poly,sign=1)
    loops=[list(r.coords)[:-1] for r in (poly.exterior,*poly.interiors)]
    mask=np.zeros_like(binary)
    cv.fillPoly(mask,[np.rint(loop).astype(np.int32) for loop in loops],1)
    region_masks[name]=mask
    grid=9 if windows else 6
    gx=np.arange(int(poly.bounds[0]),int(poly.bounds[2])+1,grid)
    gy=np.arange(int(poly.bounds[1]),int(poly.bounds[3])+1,grid)
    a,b=np.meshgrid(gx,gy);valid=contains_xy(poly,a,b)
    samples=list(zip(a[valid].tolist(),b[valid].tolist()))
    for inset in (1.7,4.3,8.5):
        inner=poly.buffer(-inset)
        for shell in (inner.geoms if inner.geom_type=='MultiPolygon' else [inner]):
            if shell.is_empty:continue
            for ring in (shell.exterior,*shell.interiors):
                count=max(4,int(ring.length/7))
                samples.extend(ring.interpolate(i/count,normalized=True).coords[0] for i in range(count))
    depths=cv.distanceTransform(mask,cv.DIST_L2,5)
    interior=[[round(float(a),3),round(float(b),3),round(float(depths[round(b),round(a)]),3)] for a,b in samples]
    regions.append(dict(name=name,loops=loops,interior=interior))

region('Upper',candidate,(300,320),True)
region('Lower',candidate,(454,681),True)
for name,seed in [('Upper1',(370,255)),('Upper2',(277,435)),('Upper3',(206,649)),
                  ('Lower1',(500,626)),('Lower2',(443,797))]:
    host='Upper' if name.startswith('Upper') else 'Lower'
    region(name,enamel*region_masks[host],seed)
(src/'traced_regions.json').write_text(json.dumps(regions,separators=(',',':')),encoding='utf8')

# Atlas uses the approval artwork's own coordinates; the reserved strip at right wraps
# the side walls and interior. Their highlights are lit by the game, not baked white.
shape=(1024,1024)
surface=np.maximum(region_masks['Upper'],region_masks['Lower']).astype(bool)
cell=np.maximum.reduce([region_masks[k] for k in region_masks if k[-1].isdigit()]).astype(bool)
_,nearest=distance_transform_edt(~surface,return_indices=True)
color=art[tuple(nearest)].astype(np.float32)
cell=cell[tuple(nearest)]
h=cv.cvtColor(color.astype('uint8'),cv.COLOR_RGB2HSV)
value=color.max(2)
weight=np.clip((h[:,:,1].astype(float)-35)/100,0,1)
blue=(h[:,:,0]>95)&(h[:,:,0]<154)&(~cell)
indigo=weight*blue
lum=color@np.array([.2126,.7152,.0722])
illum=gaussian_filter(lum,4)
micro=np.clip(lum-illum,-28,28)
silver=np.array([173,180,191])[None,None,:]+(.17*(lum-100)+.46*micro)[:,:,None]
navy=np.array([23,32,64])[None,None,:]+color*.27
mix=silver*(1-indigo[:,:,None])+navy*indigo[:,:,None]
tint=np.minimum(249,color*.90 + np.array([3,7,8]))
mix=np.where(cell[:,:,None],tint,mix)
size=1024
ar=np.zeros((*shape,3),dtype=float); ar[:,:640]=mix
orm=np.full((*shape,4),255,dtype=float)
orm[:,:640,1]=np.where(cell,49+.12*micro,86+.26*micro+18*indigo)
orm[:,:640,2]=np.where(cell,34,232-64*indigo)
orm[:,:640,3]=np.where(cell,235,0)
# Anisotropic brushing, fine optical grooves and localized luminous folds in the glaze.
yy,xx=np.mgrid[:size,:size]
rng=np.random.default_rng(11023)
grain=gaussian_filter(rng.normal(size=shape),(.46,3.2))
brushing=np.sin(yy*2.42+xx*.39+.7*np.sin(xx*.045))*.26+grain*.9
def swatch_grain(crop,frequency):
    # Remove the softbox/low-frequency colour before reusing the physical finish.
    patch=crop.astype(float)@np.array([.2126,.7152,.0722])
    patch=patch-gaussian_filter(patch,frequency)
    patch/=max(1.,np.std(patch))
    mirrored=np.block([[patch,patch[:,::-1]],[patch[::-1],patch[::-1,::-1]]])
    return mirrored[yy%mirrored.shape[0],xx%mirrored.shape[1]]
metal_fibre=swatch_grain(rgb[752:946,846:1037],2.8)
glaze_fibre=swatch_grain(rgb[753:943,1322:1507],3.6)
relief=brushing+.38*metal_fibre
relief[:,:640]+=np.where(cell,micro*.022+.74*glaze_fibre[:,:640],micro*.007)
ar[:,640:]=np.array([27,34,51]) + (brushing[:,640:]*3)[:,:,None]
ar[:,848:]=np.array([117,128,144])+(brushing[:,848:]*5)[:,:,None]
orm[:,640:,1]=144+brushing[:,640:]*8
orm[:,640:,2]=177; orm[:,640:,3]=0
orm[:,848:,1]=96+brushing[:,848:]*8
orm[:,848:,2]=226
ar[:,:640]+=brushing[:,:640,None]*1.7
ar[:,:640]+=np.where(cell[:,:,None],glaze_fibre[:,:640,None]*1.7,metal_fibre[:,:640,None]*1.2)
orm[:,:640,1]+=np.where(cell,glaze_fibre[:,:640]*2.1,metal_fibre[:,:640]*4.3)
dy,dx=np.gradient(relief)
normal=np.stack((-dx*.105,-dy*.105,np.ones(shape)),axis=2)
normal/=np.linalg.norm(normal,axis=2)[:,:,None]
em=np.zeros_like(ar)
em[:,:640]=np.where(cell[:,:,None],tint*(.24+.30*(value/255)**2)[:,:,None],0)
def save(key,img):
    img=np.uint8(np.clip(img,0,255))
    cv.imwrite(str(out/('T_Aurora_'+key+'.png')),cv.cvtColor(img,cv.COLOR_RGBA2BGRA if img.shape[2]==4 else cv.COLOR_RGB2BGR))
save('Color',ar);save('ORM',orm);save('Normal',(normal*.5+.5)*255);save('Glow',em)
print('Traced',[(r['name'],len(r['loops'])-1,len(r['interior'])) for r in regions])
