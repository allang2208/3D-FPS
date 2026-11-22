"""Build the game-art surface and UV artwork for the approved crescent concept."""
from pathlib import Path
import json
import os
import cv2
import numpy as np
import shapely
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
from scipy.ndimage import map_coordinates
from PIL import Image

HERE=Path(__file__).resolve().parent
PROJECT=Path(os.environ['FPSGAME_PROJECT'])
SOURCE=PROJECT/'SourceAssets/OneHandAxe20261101'
OUT=HERE/'Textures'
OUT.mkdir(exist_ok=True)
N=1024
SIZE=2048
HEAD='SwiftCrescent_Leaf'
ring=np.array(json.loads((SOURCE/'ModulesV1/modules.json').read_text())['interfaces']['head_grip_rings_cm'][0])/100
legacy=json.loads((SOURCE/'BladeVariants20261102/CrescentReferenceR4_20261104/SwiftCrescent.json').read_text())
scale=legacy['geometry']['dimensions_cm'][2]/(100*(940-16))
cx=(ring[:,0].max()+ring[:,0].min())/2
cy=(ring[:,1].max()+ring[:,1].min())/2
base_z=ring[0,2]
root_width=np.ptp(ring[:,0])/scale
left,right=550-root_width/2,550+root_width/2

def curve(start,*segments):
    points=[np.array(start,dtype=float)]
    for b,c,end in segments:
        a=points[-1]
        b,c,end=np.array(b),np.array(c),np.array(end)
        count=max(4,int((np.linalg.norm(a-b)+np.linalg.norm(b-c)+np.linalg.norm(c-end))/3))
        t=np.linspace(0,1,count+1)[1:,None]
        points.extend((1-t)**3*a+3*t*(1-t)**2*b+3*t*t*(1-t)*c+t**3*end)
    return np.array(points)

outer=curve((399,16),((228,96),(78,283),(84,491)),((89,645),(166,802),(302,879)))
inner=curve(outer[-1],((229,774),(226,624),(332,544)),((392,500),(446,485),(484,539)),
            ((501,590),(left,747),(left,940)))
root=np.array([[u,940] for u in np.linspace(left,right,37)])
rear=curve(root[-1],((right,775),(617,624),(631,541)),((659,440),(772,345),(845,393)),
           ((843,346),(778,298),(685,285)),((548,276),(415,254),(378,178)),
           ((353,128),(374,61),(399,16)))
outline=np.vstack([outer,inner[1:],root[1:],rear[1:-1]])
polygon=Polygon(outline)
assert polygon.is_valid

spine=curve((399,16),((338,125),(317,201),(388,271)),((470,343),(543,414),(503,506)))
# The three accents end closer to the shoulder than on Concept01.
leaves=[curve((506,493),((537,431),(586,351),(656,329))),
        curve((509,495),((550,444),(601,392),(663,375))),
        curve((512,496),((549,466),(594,431),(634,416)))]
yy,xx=np.mgrid[:N,:N].astype(np.float32)

def distance(path):
    im=np.ones((N,N),np.uint8)
    cv2.polylines(im,[np.rint(path*16).astype(np.int32)],False,0,1,cv2.LINE_8,4)
    field=cv2.distanceTransform(im,cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    return cv2.GaussianBlur(field,(0,0),1.9)

def smooth(lo,hi,val):
    t=np.clip((val-lo)/(hi-lo),0,1)
    return t*t*(3-2*t)

mask=np.zeros((N,N),np.uint8)
cv2.fillPoly(mask,[np.rint(outline*16).astype(np.int32)],1,shift=4)
border=cv2.distanceTransform(mask,cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
border=cv2.GaussianBlur(border,(0,0),3.5)
edge=distance(outer)
seam=distance(spine)
inset=curve(spine[-1],((430,516),(332,557),(285,658)),((252,728),(253,796),(302,879)))
seam_boundary=np.vstack([spine,inset[1:]])
spine_x=np.interp(yy[:,0],seam_boundary[:,1],seam_boundary[:,0])[:,None]
below=smooth(493,550,yy)
recess=(1-smooth(-4,5,xx-spine_x))*np.exp(-((xx-spine_x)/142)**2)*smooth(43,105,edge)
edge_width=10+26*np.maximum(0,np.sin(np.pi*np.clip((yy-16)/863,0,1)))**.8
silver=1-smooth(edge_width-1.8,edge_width+1.8,edge)
# High-frequency grain is reserved for shading. The actual silhouette, shoulder
# break and feather relief live on the mesh so lighting responds to camera motion.
ridge=np.zeros_like(xx)
for path in leaves:
    along=np.clip(((xx-path[0,0])*(path[-1,0]-path[0,0])+(yy-path[0,1])*(path[-1,1]-path[0,1]))/
                  np.sum((path[-1]-path[0])**2),0,1)
    taper=np.sin(np.pi*along).clip(0,1)**.72
    ridge=np.maximum(ridge,np.exp(-(distance(path)/(2.1+4.7*taper))**2)*taper)
seamlight=np.exp(-(seam/5.2)**2)*(1-below)*smooth(8,32,border)
shoulder=np.exp(-((xx-633)/198)**2-((yy-366)/156)**2)
profile=(11+13*smooth(0,38,border)+13*shoulder+6*smooth(0,163,edge)-4.5*recess
         +4.1*seamlight+5.1*ridge)
profile*=.61+.39*smooth(0,edge_width+15,edge)
profile=profile.astype(np.float32)

# Tessellate the artwork on a grid, intersecting boundary cells with the exact
# outline so the camera-facing shape is independent of texture resolution.
pitch=4.
cols,rows=np.meshgrid(np.arange(75,856,pitch),np.arange(10,941,pitch))
boxes=shapely.box(cols.ravel(),rows.ravel(),cols.ravel()+pitch,rows.ravel()+pitch)
active=boxes[shapely.intersects(boxes,polygon)]
full=shapely.covers(polygon,active)
verts=[]; indexes={}; faces=[]
def vertex(p):
    k=(round(p[0],5),round(p[1],5))
    if k not in indexes:
        indexes[k]=len(verts);verts.append(k)
    return indexes[k]
def face(p):
    ids=[vertex(v) for v in p]
    if len(set(ids))==3:faces.append(ids)
for minx,miny,maxx,maxy in shapely.bounds(active[full]):
    q=[(minx,miny),(maxx,miny),(maxx,maxy),(minx,maxy)]
    face([q[0],q[1],q[2]]);face([q[0],q[2],q[3]])
for part in shapely.intersection(active[~full],polygon):
    for tri in shapely.get_parts(shapely.constrained_delaunay_triangles(part)):
        xy=list(orient(tri,sign=1.).exterior.coords)[:3]
        if tri.area>1.e-7:face(xy)
points=np.array(verts)
u,v=points.T
height=map_coordinates(profile,[v,u],order=1,mode='nearest')*scale
wx=cx+(550-u)*scale
wz=base_z+(940-v)*scale
# Copy only the outline at the existing cosmetic grip seam. The rest of the
# visible surface is authored from the new concept. No collision geometry.
def seam_sides(x):
    x=np.clip(x,ring[:,0].min()+1e-8,ring[:,0].max()-1e-8)
    a,b=ring,np.roll(ring,-1,axis=0)
    hit=(np.minimum(a[:,0],b[:,0])<=x)&(np.maximum(a[:,0],b[:,0])>=x)&(abs(a[:,0]-b[:,0])>1e-10)
    pos=a[hit,1]+(x-a[hit,0])*(b[hit,1]-a[hit,1])/(b[hit,0]-a[hit,0])
    return (pos.min(),pos.max()) if len(pos) else (cy,cy)
neck=smooth(594,843,v)
front=cy+height;back=cy-height
for i in np.flatnonzero(neck):
    lo,hi=seam_sides(wx[i]);w=neck[i]
    front[i]=(1-w)*front[i]+w*hi;back[i]=(1-w)*back[i]+w*lo
seam_profile=np.array([seam_sides(cx+(550-col)*scale) for col in range(N)])
neck_field=smooth(594,843,yy)
shade_normals=[]
for side,rim in ((1,seam_profile[:,1]),(-1,seam_profile[:,0])):
    surf=(1-neck_field)*profile+neck_field*side*(rim[None,:]-cy)/scale
    gy,gx=np.gradient(cv2.GaussianBlur(surf.astype(np.float32),(0,0),2.2))
    gx=map_coordinates(gx,[v,u],order=1,mode='nearest')
    gy=map_coordinates(gy,[v,u],order=1,mode='nearest')
    normals=np.c_[gx,np.full(len(u),side),gy]
    shade_normals.append(normals/np.linalg.norm(normals,axis=1)[:,None])
np.savez_compressed(HERE/'surface.npz',points=points,front=np.c_[wx,front,wz],back=np.c_[wx,back,wz],
                    normals=np.vstack(shade_normals),faces=np.array(faces))

# Both sides use independent UV islands. The grain follows the silhouette,
# while the glyphs on the reverse stay readable in the opposite view.
rng=np.random.default_rng(54)
noise=rng.normal(0,1,(N,N)).astype(np.float32)
large=cv2.GaussianBlur(noise,(0,0),28)*60
direction=cv2.GaussianBlur(noise,(1,21),0)
grain=np.clip(.32*noise+.65*direction+.20*np.sin(.54*edge+.07*large),-1.6,1.6)
focus=np.clip(.27*ridge+.42*seamlight+silver,0,1)
body=np.array([.194,.223,.256],np.float32)
graphite=np.array([.069,.082,.099],np.float32)
polish=np.array([.585,.617,.64],np.float32)
color=body+(graphite-body)*recess[:,:,None]
color=color*(1-focus[:,:,None])+polish*focus[:,:,None]
color*=1+(.018*grain+.023*large)[:,:,None]
rough=np.clip(.352+.145*recess-.095*silver-.045*ridge+.025*grain+.012*large,.16,.68)
micro=np.asarray(.51*direction+.15*noise+.12*silver*np.cos(.54*edge+.17*large),np.float32)
gy,gx=np.gradient(micro)
normal=np.dstack([-.067*gx,.067*gy,np.ones_like(gx)])
normal/=np.linalg.norm(normal,axis=2,keepdims=True)
def atlas(c,n):
    # Flip U on reverse; tangent-space X is reversed as well for the normal.
    reverse=c[:,::-1].copy()
    if n=='Normal':reverse[:,:,0]=1-reverse[:,:,0]
    both=np.concatenate([c,reverse],axis=1)
    img=Image.fromarray(np.uint8(np.clip(both,0,1)*255+.5))
    img.resize((SIZE,SIZE),Image.Resampling.BILINEAR).save(OUT/f'T_{HEAD}_{n}.png')
atlas(np.where(color<=.0031308,12.92*color,1.055*color**(1/2.4)-.055),'BaseColor')
atlas(np.dstack([1-.065*ridge,rough,np.full_like(rough,.985)]),'ORM')
atlas(normal*.5+.5,'Normal')

# The project glyph source is an existing graphic. Place it upright on the
# broad uncluttered field and mirror the UV placement on the reverse island.
symbol_source=json.loads((SOURCE/'CommonRunes20261104/sources.json').read_text())
for rune in symbol_source['runes']:
    ref=Image.open(rune['glyph']).convert('RGBA')
    data=np.array(ref)
    luminance=np.mean(data[:,:,:3].astype(np.float32)/255,axis=2)
    alpha=np.uint8(255*(luminance*(data[:,:,3].astype(np.float32)/255)>.92))
    glyph=Image.fromarray(alpha)
    bbox=glyph.getbbox()
    if not bbox:raise ValueError(rune['id'])
    glyph=glyph.crop(bbox);glyph.thumbnail((124,124),Image.Resampling.LANCZOS)
    w,h=glyph.size
    tile=Image.new('L',(N,N));tile.paste(glyph,(264-w//2,435-h//2))
    reverse=Image.new('L',(N,N));reverse.paste(glyph,(N-264-w//2,435-h//2))
    out=Image.new('L',(N*2,N));out.paste(tile,(0,0));out.paste(reverse,(N,0))
    out.resize((SIZE,SIZE),Image.Resampling.BILINEAR).save(OUT/f'T_{HEAD}_{rune["kind"]}.png')
