"""Bake object-space surfaces into the unique UV atlas using the exported Mikk basis."""
from pathlib import Path
import tempfile, math
import cv2, numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from scipy.interpolate import PchipInterpolator
from numba import njit, prange, set_num_threads
set_num_threads(6)
out = Path(__file__).resolve().parents[1] / 'Textures'
work = Path(tempfile.gettempdir()) / 'M24MeshyCarbon1105124237_finish'
data = np.load(work/'basis.npz')
pos,tri,uv,tan,normal,sign,ao = [data[k] for k in ('pos','ids','uv','tangent','normal','sign','ao')]
size=4096
# Parametrize the exterior against a smooth neutral mould. The side weave keeps
# its pitch through the sculpted recess; only the top roll turns it across the crown.
stations=np.linspace(-.949,.949,241)
tops=[]; widths=[]
for x in stations:
    section=pos[np.abs(pos[:,0]-x)<.012]
    tops.append(np.quantile(section[:,2],.99))
    widths.append(np.quantile(np.abs(section[:,1]),.96))
tops=gaussian_filter(np.array(tops),3.5)
widths=gaussian_filter(np.array(widths),4.5)
# Cheek contact seam traced on the Meshy surface, not from a rectangular UV mask.
side_x=np.array([305,319,349,381,424,477,547,593,695,990,1270,1340,1371,1392,1415,1431,1447,1460,1471,1478,1480])
side_z=np.array([113,120,133,146,158,168,174,177,178,177,177,177,176,173,165,155,138,116,90,76,71])
edge_x=np.linspace((305-825)/790,(1480-825)/790,1024)
cheek_edge=PchipInterpolator((side_x-825)/790,(327-side_z)/790)(edge_x)
@njit
def weave_distance(x,y,z):
    ux=min(239.999999,max(0.,(x+.949)*240/1.898))
    i=int(ux); f=ux-i
    top=tops[i]*(1-f)+tops[i+1]*f
    width=widths[i]*(1-f)+widths[i+1]*f
    drop=max(0.,top-z)
    # Smoothly unfold the rounded crown into the two broad, nearly planar sides.
    trans=min(1.,drop/.08)
    trans=trans*trans*(3.-2.*trans)
    length=(abs(y)*(1.-trans)+(width+drop)*trans)
    return length if y<0 else -length
@njit
def hashed(i,j,k):
    a=(i*73856093 ^ j*19349663 ^ k*83492791)&0xffffffff
    a=((a^(a>>16))*2246822519)&0xffffffff
    a=((a^(a>>13))*3266489917)&0xffffffff
    return ((a^(a>>16))&65535)/65535.
@njit
def grain(x,y,z,rate):
    x=x*rate+251.23;y=y*rate+501.43;z=z*rate+201.37
    i=math.floor(x);j=math.floor(y);k=math.floor(z)
    a=x-i;b=y-j;c=z-k
    a=a*a*(3-2*a);b=b*b*(3-2*b);c=c*c*(3-2*c)
    v=0.
    for u in range(2):
        for t in range(2):
            for s in range(2):
                v+=hashed(i+u,j+t,k+s)*(a if u else 1-a)*(b if t else 1-b)*(c if s else 1-c)
    return v
@njit
def material_id(x,z):
    if x<-.8448: return 3
    if x>.8304: return 2
    if x>edge_x[0] and x<edge_x[-1]:
        t=(x-edge_x[0])/(edge_x[-1]-edge_x[0])*1023
        i=min(int(t),1022)
        bound=cheek_edge[i]+(t-i)*(cheek_edge[i+1]-cheek_edge[i])
        if z>=bound: return 1
    return 0
@njit
def surface(x,y,z,m):
    if m==0:
        dist=weave_distance(x,y,z)
        u=x/.0063 + .055*math.sin(dist*46.+x*3.)
        v=dist/.0063 + .047*math.sin(x*39.+dist*8.)
        i=math.floor(u);j=math.floor(v)
        fu=u-i;fv=v-j
        warp=(i-j)%4<2
        across=fv if warp else fu
        along=(u-j)%4 if warp else (v-i-1)%4
        crown=math.sin(math.pi*across)**.64
        bridge=.78+.22*math.sin(math.pi*(along+.1)/2)
        filament=.5+.5*math.sin(2*math.pi*(across*4+.07*math.sin(along*2.7)))
        drift=math.sin(.87*i+.24*j)*math.cos(.13*i-.97*j)
        depth=crown*bridge
        base=21+(42 if warp else 17)*depth+3*filament*crown+2.2*drift
        rough=.425-(.095 if warp else .066)*depth+.015*(.5-filament)
        height=.00015*depth+.000022*(filament-.5)*crown
        return base,rough,0.,height
    if m==3:
        # Very fine axial satin tooling around the neck, softly broken by blast grain.
        a=grain(x,y,z,700.); b=grain(x*2.7,y*.31,z*.31,350.)
        return 76+5*(a-.5)+4*(b-.5),.36+.046*(b-.5),.89,.000040*(a-.5)+.000045*(b-.5)
    a=grain(x,y,z,475. if m==1 else 385.)
    b=grain(x,y,z,1100.)
    slow=grain(x,y,z,49.)
    if m==1:
        return 36+7*(a-.5)+2.5*(b-.5)+2*(slow-.5),.59+.06*(a-.5)+.03*(slow-.5),0.,.00021*(a-.5)+.000056*(b-.5)
    return 30+6*(a-.5)+3*(slow-.5),.745+.065*(a-.5),0.,.00025*(a-.5)+.000060*(b-.5)
@njit
def rast(uv,sz):
    ix=np.full((sz,sz),-1,np.int32)
    ab=np.zeros((sz,sz,2),np.float32)
    for i in range(len(uv)//3):
        a,b,c=uv[3*i:3*i+3]
        ax,ay=a[0]*sz-.5,(1-a[1])*sz-.5
        bx,by=b[0]*sz-.5,(1-b[1])*sz-.5
        cx,cy=c[0]*sz-.5,(1-c[1])*sz-.5
        det=(bx-ax)*(cy-ay)-(cx-ax)*(by-ay)
        if abs(det)<1.e-10: continue
        for y in range(max(0,math.ceil(min(ay,by,cy))),min(sz,math.floor(max(ay,by,cy))+1)):
            for x in range(max(0,math.ceil(min(ax,bx,cx))),min(sz,math.floor(max(ax,bx,cx))+1)):
                w=((x-ax)*(cy-ay)-(y-ay)*(cx-ax))/det; v=((y-ay)*(bx-ax)-(x-ax)*(by-ay))/det
                if min(w,v,1-w-v)>=-.000001:
                    ix[y,x]=i; ab[y,x,0]=w; ab[y,x,1]=v
    return ix,ab
@njit(inline='always')
def norm(a,b,c):
    inv=1./max(1.e-12,math.sqrt(a*a+b*b+c*c))
    return a*inv,b*inv,c*inv
@njit(inline='always')
def blend3(arr,i0,i1,i2,a,b,c):
    return (a*arr[i0,0]+b*arr[i1,0]+c*arr[i2,0],a*arr[i0,1]+b*arr[i1,1]+c*arr[i2,1],a*arr[i0,2]+b*arr[i1,2]+c*arr[i2,2])
@njit(parallel=True)
def paint(ix,ab,pos,tri,tan,normal,sign,ao):
    h,w=ix.shape
    col=np.zeros((h,w,3),np.uint8); orm=col.copy(); nmap=col.copy()
    e=.00033
    for row in prange(h):
        for j in range(w):
            k=ix[row,j]
            if k<0: continue
            b,c=ab[row,j]; a=1.-b-c
            i0,i1,i2=tri[k]
            x,y,z=blend3(pos,i0,i1,i2,a,b,c)
            m=material_id(x,z)
            val,r,metal,ht=surface(x,y,z,m)
            col[row,j,0]=round(val*(.965 if m in (0,3) else 1.))
            col[row,j,1]=round(val*.99)
            col[row,j,2]=round(val*(1.024 if m in (0,3) else .98))
            orm[row,j,0]=round(255*(a*ao[i0]+b*ao[i1]+c*ao[i2]))
            orm[row,j,1]=round(255*r); orm[row,j,2]=round(255*metal)
            l=3*k
            n0,n1,n2=blend3(normal,l,l+1,l+2,a,b,c)
            n0,n1,n2=norm(n0,n1,n2)
            t0,t1,t2=blend3(tan,l,l+1,l+2,a,b,c)
            dot=t0*n0+t1*n1+t2*n2
            t0,t1,t2=norm(t0-dot*n0,t1-dot*n1,t2-dot*n2)
            s=sign[l,0]
            b0,b1,b2=s*(n1*t2-n2*t1),s*(n2*t0-n0*t2),s*(n0*t1-n1*t0)
            dt=(surface(x+t0*e,y+t1*e,z+t2*e,m)[3]-surface(x-t0*e,y-t1*e,z-t2*e,m)[3])/(2*e)
            db=(surface(x+b0*e,y+b1*e,z+b2*e,m)[3]-surface(x-b0*e,y-b1*e,z-b2*e,m)[3])/(2*e)
            nx,ny,nz=norm(-dt,-db,1.)
            nmap[row,j,0]=round(127.5*(1+nx));nmap[row,j,1]=round(127.5*(1+ny));nmap[row,j,2]=round(127.5*(1+nz))
    return col,orm,nmap
print('Rasterizing unique UV triangles',flush=True)
index,ab=rast(uv,size)
print('Baking surface layers, roughness and tangent slopes',flush=True)
col,orm,nmap=paint(index,ab,pos,tri,tan,normal,sign,ao)
# Extend texels beyond island edges to prevent filtering against the atlas background.
inside=index>=0
d,labels=cv2.distanceTransformWithLabels((~inside).astype(np.uint8),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
rim=(~inside)&(d<=32)
nearest=labels[rim]-1
for image,name,bg in ((col,'BaseColor',(37,37,38)),(orm,'ORM',(255,120,0)),(nmap,'NormalGL',(128,128,255))):
    image[rim]=image[inside][nearest]
    image[~(inside|rim)]=bg
    Image.fromarray(image).save(out/('T_Xuanji_'+name+'_4K.png'),compress_level=5)
    if name=='NormalGL':
        image[:,:,1]=255-image[:,:,1]
        Image.fromarray(image).save(out/'T_Xuanji_NormalDX_4K.png',compress_level=5)
print('PBR atlases written.',flush=True)
