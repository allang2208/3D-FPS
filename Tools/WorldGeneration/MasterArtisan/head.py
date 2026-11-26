"""Fit the Jason head and neck, transfer the three photographic views into its UVs, and make the spectacles and knot."""
import cv2
import argparse
import numpy as np
from numba import njit
from scipy.ndimage import distance_transform_edt
from pattern import Piece, SRC, STRONG, SMITH, normalized, read

parser=argparse.ArgumentParser()
parser.add_argument("--refined",action="store_true",help="Build the R3 fine sculpt from the original long-haired face")
refined=parser.parse_args().refined
output=SRC/"HeadR3" if refined else SRC

native=read(STRONG/"R2_LongLegs/head_source.json")
rig=read(SMITH/"BodyOutfit/outfit.json")["bones"]
bone_ids={b["name"]:i for i,b in enumerate(rig)}
remap=[]
for bone in native["bones"]:
    while bone["name"] not in bone_ids:
        bone=native["bones"][bone["parent"]]
    remap.append(bone_ids[bone["name"]])
weights=[]
for row in native["weights"]:
    mix={}
    for b,x in row:
        k=remap[b]
        mix[k]=mix.get(k,0)+x
    weights.append([[k,round(v,7)] for k,v in sorted(mix.items())])
rigid=lambda _: [[bone_ids["head"],1.]]
p=np.array(native["positions"])+[0,0,4.5]
x,y,z=p.T.copy()
front=np.clip((y-2)/6,0,1)
# Preserve the actual R4 neck vertices below the jaw. Give the temples, jaw and swept-back crown their own silhouette.
p[:,0]+=.48*np.tanh(x/3)*np.exp(-((z-160.1)/2.8)**2)*front
p[:,1]-=.28*np.exp(-((z-169.1)/1.25)**2)*front
hair=np.clip((z-170.7)/6,0,1)
p[:,2]+=.92*hair
p[:,1]-=.9*hair
if refined:
    # Millimetre-scale changes to the R1 surface. Preserve the neck, eye seats, hinge fit and original chin taper.
    a=np.abs(x+.20)
    def bell(value,center,width):
        return np.exp(-((value-center)/width)**2)
    cheek=front*bell(a,5.45,1.85)*bell(z,165.1,1.8)
    corner=np.clip((y+1)/5,0,1)*bell(a,5.35,2.15)*bell(z,159.9,1.95)
    tip=front*bell(a,0,1.28)*bell(z,164.75,1.0)
    wing=front*bell(a,1.15,.72)*bell(z,164.65,.9)
    p[:,0]+=np.tanh((x+.2)*1.35)*(.20*corner+.085*cheek+.09*wing)
    p[:,1]+=.23*cheek+.075*corner-.115*tip
    p[:,2]+=.075*cheek+.065*tip
tri=np.array(native["triangles"])
uv=np.array(native["triangle_uvs"])
m=np.array(native["triangle_materials"])
normal=np.zeros_like(p)
for mat in np.unique(m):
    f=tri[m==mat]
    fn=np.cross(p[f[:,2]]-p[f[:,0]],p[f[:,1]]-p[f[:,0]])
    for j in range(3): np.add.at(normal,f[:,j],fn)
normal=normalized(normal)

sheet=cv2.imread(str(output/"HeadTurnaround.png"))
original=cv2.imread(str(SRC/"HeadTurnaround.png")) if refined else None
views=[]
for i in range(3):
    pic=sheet[:,724*i:724*(i+1)].copy()
    cv2.imwrite(str(output/(["Front","Left","Back"][i]+".png")),pic)
    if refined:
        # The presentation sheet shows a cloth collar. Keep the R1 bare neck at the actual body interface.
        start,end=[(565,603),(546,602),(530,587)][i]
        t=np.clip((np.arange(pic.shape[0])-start)/(end-start),0.,1.)[:,None,None]
        t=t*t*(3.-2.*t)
        pic=np.uint8(np.round(pic*(1.-t)+original[:,724*i:724*(i+1)]*t))
    bg=np.median(pic[200:550,:12].reshape(-1,3),axis=0)
    delta=np.linalg.norm(pic.astype(float)-bg,axis=2)
    mask=np.uint8(delta>24)*255
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((11,11),np.uint8))
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    mask[:]=0
    cv2.drawContours(mask,[max(contours,key=cv2.contourArea)],0,255,-1)
    mask=cv2.erode(mask,np.ones((7,7),np.uint8))
    iy,ix=distance_transform_edt(mask==0,return_distances=False,return_indices=True)
    pic=pic[iy,ix]
    ink=np.zeros(pic.shape[:2],np.uint8)
    if i==0:
        for path in [[(169,292),(183,276),(225,269),(308,264),(340,265),(364,278),(384,273),(403,262),(493,258),(538,259),(550,273)],[(187,276),(195,303),(202,335),(218,349),(259,352),(298,346),(318,338),(330,318),(341,279)],[(398,276),(402,307),(412,330),(426,339),(470,343),(500,340),(520,330),(529,309),(538,272)]]:
            cv2.polylines(ink,[np.int32(path)],False,255,12,cv2.LINE_AA)
    elif i==1:
        cv2.polylines(ink,[np.int32([(121,274),(132,266),(161,270),(184,276),(287,282),(363,281),(392,287),(407,297)])],False,255,12,cv2.LINE_AA)
        cv2.polylines(ink,[np.int32([(129,274),(129,312),(135,340),(145,346),(153,339),(158,291)])],False,255,8,cv2.LINE_AA)
    if ink.any():pic=cv2.inpaint(pic,ink,6,cv2.INPAINT_TELEA)
    views.append(pic)

@njit
def raster(positions,uvs,original,images):
    out=original.copy()
    H,W=out.shape[:2]
    valid=np.zeros((H,W),np.uint8)
    for i in range(len(positions)):
        a,b,c=uvs[i]*np.array([W,H])-.5
        ab=b-a;ac=c-a;den=ab[0]*ac[1]-ab[1]*ac[0]
        if abs(den)<1.e-7:continue
        for yy in range(max(0,int(np.floor(min(a[1],b[1],c[1])))),min(H,int(np.ceil(max(a[1],b[1],c[1])))+1)):
            for xx in range(max(0,int(np.floor(min(a[0],b[0],c[0])))),min(W,int(np.ceil(max(a[0],b[0],c[0])))+1)):
                dx,dy=xx-a[0],yy-a[1]
                u=(dx*ac[1]-dy*ac[0])/den;v=(ab[0]*dy-ab[1]*dx)/den
                if min(u,v,1-u-v)<-.001:continue
                x,y,z=positions[i,0]*(1-u-v)+positions[i,1]*u+positions[i,2]*v
                fade=min(1.,max(0.,(z-151.6)/5.))
                if fade<=0:continue
                az=np.arctan2(abs(x+.20),(y-1.55)*.91)
                sw=min(1.,max(0.,(az-.73)/.55))
                bw=min(1.,max(0.,(az-1.93)/.61))
                sw=sw*sw*(3-2*sw);bw=bw*bw*(3-2*bw)
                blend=(1-sw,sw*(1-bw),bw)
                xs=np.interp(abs(x+.20),np.array([0.,3.2,6.3,8.,10.]),np.array([0.,81.,153.,184.,218.]))*np.sign(x+.20)
                fz=np.interp(z,np.array([151.,155.,157.,158.7,161.05,162.,164.8,169.05,171.4,176.,180.5]),np.array([720.,684.,608.,552.,491.,468.,405.,299.,248.,129.,10.]))
                sy=np.interp(z,np.array([151.,155.,157.,158.7,161.1,164.8,169.05,176.,180.5]),np.array([720.,685.,610.,554.,489.,390.,295.,125.,9.]))
                coords=((370.+xs,fz),(410.-y*24.3,sy),(366.-xs,sy))
                for ch in range(3):
                    val=0.
                    for k in range(3):
                        sx=min(722.99,max(.0,coords[k][0]));vy=min(722.99,max(.0,coords[k][1]))
                        ix,iy=int(sx),int(vy);fx,fy=sx-ix,vy-iy
                        val+=blend[k]*((images[k,iy,ix,ch]*(1-fx)+images[k,iy,ix+1,ch]*fx)*(1-fy)+(images[k,iy+1,ix,ch]*(1-fx)+images[k,iy+1,ix+1,ch]*fx)*fy)
                    out[yy,xx,ch]=np.uint8(min(255.,max(0.,original[yy,xx,ch]*(1-fade)+val*fade)))
                valid[yy,xx]=255
    return out,valid

base=cv2.imread(str(SMITH/"BodyOutfit/Textures/T_Smith_Skin_head_BC.png"))
base=cv2.resize(base,(2048,2048),interpolation=cv2.INTER_AREA)
out,mask=raster(p[tri[m==0]],uv[m==0],base,np.stack(views))
near=cv2.dilate(mask,np.ones((11,11),np.uint8))>mask
iy,ix=distance_transform_edt(mask==0,return_distances=False,return_indices=True)
out[near]=out[iy[near],ix[near]]
cv2.imwrite(str(output/"T_ArtisanHead.png"),out)
# The knot keeps its own densely combed photographic material and a narrow indigo tie.
patch=views[2][92:235,246:440]
if not refined:
    cv2.imwrite(str(output/"T_ArtisanHair.png"),cv2.resize(patch,(256,256),interpolation=cv2.INTER_CUBIC))

piece=Piece()
mats=["Head"]+[q["asset"].split(".")[0] for q in native["materials"][1:]]+["Frame","Hair","Indigo","Brass","Lens"]
for i,t in enumerate(tri):
    piece.face([piece.corner(p[k],normal[k],uv[i,j],weights[k]) for j,k in enumerate(t)],int(m[i]))
# Rounded rectangular spectacles. The clear opening leaves the actual animated eye surface visible.
for side in (-1,1):
    theta=np.linspace(0,2*np.pi,73)
    dx=2.88*np.sign(np.cos(theta))*np.abs(np.cos(theta))**.55
    dz=1.62*np.sign(np.sin(theta))*np.abs(np.sin(theta))**.54
    gx=side*(3.61+dx)-.2
    gy=12.18-.057*(gx+.2)**2
    piece.tube(np.column_stack([gx,gy,169.04+dz+.045*dx]),.165,8,rigid)
    contour=[]
    for a,b,c in zip(gx[:-1],gy[:-1],(169.04+dz+.045*dx)[:-1]):
        contour.append(piece.corner([a,b,c],[0,1,0],[(a+8)/16,(c-166)/6],rigid(None)))
    center=piece.corner([side*3.61-.2,11.65,169.04],[0,1,0],[.5,.5],rigid(None))
    for j,k in enumerate(contour):
        edge=(center,k,contour[(j+1)%len(contour)])
        piece.face(edge if side==1 else edge[::-1],12)
    e=side*6.44-.2
    curve=np.array([[e,9.94,169.78],[side*7.45-.2,8.70,169.82],[side*8.28-.2,6.12,169.71],[side*8.74-.2,2.3,169.42],[side*8.7-.2,.08,169.11],[side*8.50-.2,-1.25,168.17]])
    piece.tube(curve,.145,8,rigid)
    piece.tube([curve[0]+[0,.02,.03],curve[1]+[0,.02,.03]],.17,11,rigid)
piece.tube([[-.95,12.20,169.64],[-.57,12.5,169.87],[-.16,12.66,169.94],[.28,12.52,169.84],[.67,12.22,169.66]],.17,8,rigid)
a=np.linspace(0,2*np.pi,57)
b=np.linspace(.015,np.pi-.015,34)
knot=[np.column_stack([3.05*np.sin(t)*np.cos(a)-.10,-8.78+3.35*np.sin(t)*np.sin(a),166.45+2.28*np.cos(t)+.25*np.sin(a*3)*np.sin(t)]) for t in b]
piece.grid(knot,rigid,9,(2.,1.),radial=True)
piece.tube(np.column_stack([2.44*np.cos(a)-.1,-7.05+0*a,166.72+1.88*np.sin(a)]),.29,10,rigid)
piece.save("Head",mats,output)
