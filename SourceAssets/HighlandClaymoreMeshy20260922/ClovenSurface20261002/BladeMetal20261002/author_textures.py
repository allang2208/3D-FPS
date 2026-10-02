"""Reproject the blade's existing metal PBR onto the continuous horn UVs."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

P = Path(__file__).resolve().parent
SRC = P.parents[1] / 'Meshy/candidate01/downloads'
SIZE = 2048
MASK_SIZE = 2048
data = np.load(P / 'surface_transfer.npz')
blade = np.load(P / 'blade_steel_transfer.npz')
maps = {key: np.asarray(Image.open(SRC / name).convert('RGB'), dtype=np.float32)/255.
    for key, name in [('base', 'texture_0.png'), ('normal', 'texture_0_normal.png'),
                      ('metal', 'texture_0_metallic.png'), ('rough', 'texture_0_roughness.png')]}
maps['base'] = np.where(maps['base'] <= .04045, maps['base']/12.92, ((maps['base']+.055)/1.055)**2.4)

def triangle_pixels(triangle, size):
    a, b, c = triangle*size
    lo, hi = np.floor(np.min([a,b,c], axis=0)).astype(int), np.ceil(np.max([a,b,c], axis=0)).astype(int)
    lo[0], hi[0] = max(0,lo[0]), min(size-1,hi[0])
    if hi[0] < lo[0] or hi[1] < lo[1]:
        return None
    gx, gy = np.meshgrid(np.arange(lo[0],hi[0]+1), np.arange(lo[1],hi[1]+1))
    q = np.column_stack((gx.ravel()+.5,gy.ravel()+.5))-a
    e1, e2 = b-a,c-a
    det = e1[0]*e2[1]-e1[1]*e2[0]
    if abs(det)<1.e-9:
        return None
    w1=(q[:,0]*e2[1]-q[:,1]*e2[0])/det
    w2=(e1[0]*q[:,1]-e1[1]*q[:,0])/det
    w0=1-w1-w2
    hit=(w0>=-1.e-5)&(w1>=-1.e-5)&(w2>=-1.e-5)
    return gx.ravel()[hit],size-1-(gy.ravel()[hit]%size),np.column_stack((w0,w1,w2))[hit]

mask=np.zeros((MASK_SIZE,MASK_SIZE),dtype=bool)
owner=np.full(mask.shape,-1,dtype=np.int32)
for i,triangle in enumerate(blade['uv']):
    pixels=triangle_pixels(triangle,MASK_SIZE)
    if pixels is None:
        continue
    xx,yy,w=pixels
    mask[yy,xx]=True
    owner[yy,xx]=i
small=np.asarray(Image.open(SRC/'texture_0.png').convert('RGB').resize((MASK_SIZE,MASK_SIZE)),dtype=np.float32)/255.
metal=np.asarray(Image.open(SRC/'texture_0_metallic.png').convert('L').resize((MASK_SIZE,MASK_SIZE)),dtype=np.float32)/255.
# UV membership selects actual blade faces; colour and metal identity exclude
# native glyphs, trim and island padding from the reusable steel patch.
mask &= (np.ptp(small,axis=2)<.09)&(small.mean(axis=2)>.28)&(small.mean(axis=2)<.82)&(metal>.5)
distance=distance_transform_edt(mask)
cy,cx=np.unravel_index(distance.argmax(),distance.shape)
radius=max(2,int(distance[cy,cx]*.64))
if not mask[cy,cx] or distance[cy,cx]<3:
    raise RuntimeError('Blade has no isolated steel swatch large enough to transfer')
source_size=maps['base'].shape[0]
scale=source_size/MASK_SIZE
x0,x1=int((cx-radius)*scale),int((cx+radius+1)*scale)
y0,y1=int((cy-radius)*scale),int((cy+radius+1)*scale)
tile={key:value[int(y0/source_size*value.shape[0]):int(y1/source_size*value.shape[0]),
                int(x0/source_size*value.shape[1]):int(x1/source_size*value.shape[1])].copy()
      for key,value in maps.items()}

# Make only the small patch boundary periodic; its metal colour, roughness and
# normal grain come from the sword rather than a procedural replacement.
for patch in tile.values():
    h,w=patch.shape[:2]
    band=max(2,min(h,w)//8)
    for i in range(band):
        weight=.5*(1-i/band)**2
        a,b=patch[:,i].copy(),patch[:,w-1-i].copy()
        patch[:,i]=a*(1-weight)+b*weight
        patch[:,w-1-i]=b*(1-weight)+a*weight
        a,b=patch[i].copy(),patch[h-1-i].copy()
        patch[i]=a*(1-weight)+b*weight
        patch[h-1-i]=b*(1-weight)+a*weight
index=int(owner[cy,cx])
tex=blade['uv'][index]
points=blade['points'][index]
derivative=np.column_stack((points[1]-points[0],points[2]-points[0])) @ np.linalg.inv(np.column_stack((tex[1]-tex[0],tex[2]-tex[0])))
patch_meters=np.maximum(np.linalg.norm(derivative,axis=0)*np.array([(x1-x0)/source_size,(y1-y0)/source_size]),.003)
yy,xx=np.mgrid[:SIZE,:SIZE]
uu=(xx+.5)/SIZE
vv=1-(yy+.5)/SIZE
# Each half-atlas contains one approximately 20 cm horn; circumference is
# approximately 7 cm. Transfer repeat counts retain the blade grain's scale.
tu=((uu-.025)% .5)/.45 * (.20/patch_meters[0])
tv=vv*(.07/patch_meters[1])

def sample(image,coords,repeat=False):
    h,w=image.shape[:2]
    if repeat:
        coords=coords%1.
    px=np.clip(coords[:,0],0.,1.)*(w-1)
    py=(1-np.clip(coords[:,1],0.,1.))*(h-1)
    ix,iy=px.astype(int),py.astype(int)
    jx,jy=np.minimum(ix+1,w-1),np.minimum(iy+1,h-1)
    a,b=(px-ix)[:,None],(py-iy)[:,None]
    return (image[iy,ix]*(1-a)+image[iy,jx]*a)*(1-b)+(image[jy,ix]*(1-a)+image[jy,jx]*a)*b

coords=np.column_stack((tu.ravel(),tv.ravel()))
steel={key:sample(patch,coords,True).reshape(SIZE,SIZE,3) for key,patch in tile.items()}
out={key:np.zeros((SIZE,SIZE,3),dtype=np.float32) for key in maps}
filled=np.zeros((SIZE,SIZE),dtype=bool)

def frame(p,tex):
    a,b=p[1]-p[0],p[2]-p[0]
    ta,tb=tex[1]-tex[0],tex[2]-tex[0]
    det=ta[0]*tb[1]-ta[1]*tb[0]
    if abs(det)<1.e-12:
        return np.eye(3)
    n=np.cross(a,b);n/=max(np.linalg.norm(n),1.e-12)
    t=(a*tb[1]-b*ta[1])/det;t-=n*np.dot(t,n);t/=max(np.linalg.norm(t),1.e-12)
    bit=np.cross(n,t)
    if np.dot(bit,(-a*tb[0]+b*ta[0])/det)<0:bit*=-1
    return np.stack((t,bit,n),axis=1)

for i,triangle in enumerate(data['uv']):
    pixels=triangle_pixels(triangle,SIZE)
    if pixels is None:
        continue
    xx,yy,w=pixels
    old_coords=w@data['old_uv'][i]
    root=np.clip(w@data['blend'][i],0.,1.)[:,None]
    rim=np.clip(w@data['ornament'][i],0.,1.)[:,None]
    body=root*(1-rim)
    for key in ['base','rough','metal']:
        previous=sample(maps[key],old_coords)
        out[key][yy,xx]=previous*(1-body)+steel[key][yy,xx]*body
    previous=sample(maps['normal'],old_coords)*2-1
    conversion=frame(data['points'][i],triangle).T@frame(data['points'][i],data['old_uv'][i])
    previous=previous@conversion.T
    previous[:,2]=np.maximum(previous[:,2],.15)
    previous/=np.maximum(np.linalg.norm(previous,axis=1,keepdims=True),1.e-8)
    transferred=steel['normal'][yy,xx]*2-1
    # Decorative rim keeps the prior refinement's restrained relief. The wing
    # field uses the actual sword metal normal at its original strength.
    n=previous*((1-root)+root*rim*.32)+transferred*(body+root*rim*.68)
    n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1.e-8)
    out['normal'][yy,xx]=n*.5+.5
    filled[yy,xx]=True
nearest=distance_transform_edt(~filled,return_distances=False,return_indices=True)
for key,pixels in out.items():
    pixels[~filled]=pixels[nearest[0][~filled],nearest[1][~filled]]
    if key=='base':pixels=np.where(pixels<=.0031308,pixels*12.92,1.055*np.maximum(pixels,0.)**(1/2.4)-.055)
    suffix={'base':'BaseColor','normal':'Normal','rough':'Roughness','metal':'Metallic'}[key]
    Image.fromarray(np.uint8(np.clip(pixels,0.,1.)*255+.5)).save(P/'Textures'/('T_ClovenBladeMetal_'+suffix+'.png'))
(P/'texture_recipe.json').write_text(json.dumps({'source':'Original blade metal texture_0 PBR',
    'swatch_pixels':[x0,y0,x1,y1],'swatch_physical_m':patch_meters.tolist(),'size':SIZE,
    'body_parameters':'Transferred source BaseColor/Normal/Metallic/Roughness without material retuning',
    'normal_convention':'OpenGL; flip green once on UE import','tested':False},indent=2),encoding='utf-8')
print('CLOVEN_BLADE_TEXTURES_AUTHORED '+str([x0,y0,x1,y1]),flush=True)
