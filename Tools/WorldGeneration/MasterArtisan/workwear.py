"""Cut the work robe to the R4 work shirt, retaining its fitted sleeves, boot clearance and leg weights."""
import argparse
import cv2
import numpy as np
from scipy.spatial import cKDTree
from pattern import Piece, SMITH, SRC, normalized, read

parser=argparse.ArgumentParser()
parser.add_argument("--refined",action="store_true",help="Cut the R5 collar and sew the fitted tool pocket")
parser.add_argument("--review-fit",action="store_true",help="Apply the R6 corrections from the posed UE close-ups")
args=parser.parse_args()
refined=args.refined or args.review_fit
output=SRC/"WorkwearR6" if args.review_fit else SRC/"WorkwearR5" if refined else SRC
if refined:
    from workwear_finish import wrap_collar, apron_details

data=read(SMITH/"FinishR2/BodyOutfit/outfit.json")
p=np.array(data["positions"])
tri=np.array(data["triangles"])
materials=["Indigo","Twill","Apron","Saddle","Boot","Sole","Brass","Thread","Flax","Lapel","Toolwood","Iron"]
if refined:materials.append("WaxThread")
piece=Piece()
parts=data["parts"]
def sample_part(name):
    a,_,b,_=parts[name]
    return p[a:b],np.arange(a,b)
shirt,shirt_ids=sample_part("Continuous linen shirt")
pants,pants_ids=sample_part("trousers")
surface=np.vstack([shirt,pants])
surface_ids=np.r_[shirt_ids,pants_ids]
tree=cKDTree(surface)
def bind(point):
    dist,idx=tree.query(point,k=4)
    blend=1/(dist+.12)**2
    merged={}
    for source,coef in zip(surface_ids[idx],blend/blend.sum()):
        for bone,weight in data["weights"][source]:
            merged[bone]=merged.get(bone,0)+coef*weight
    pairs=sorted(merged.items(),key=lambda pair:-pair[1])[:8]
    total=sum(q[1] for q in pairs)
    return [[int(k),round(float(v/total),7)] for k,v in pairs]

# Retain the two-sided lower apron with its existing split, edge piping and repair stitches.
for name,(_,start,_,end) in parts.items():
    if refined:
        if name=="Continuous linen shirt":
            wrap_collar(piece,data,args.review_fit)
            continue
        if name=="Soft collar stand with inner facing" or name.startswith(("Old oblique","Whip stitch")):continue
    apron=name in ("Cut leather bib and vented apron","Leather reverse","Rounded cut leather edges and vent")
    supported=name in ("Continuous linen shirt","Soft collar stand with inner facing","trousers","boots","Skived and rounded waist belt") or name.startswith(("Twice turned sleeve","Old oblique","Whip stitch","Flat-felled"))
    if not (apron or supported):continue
    for i in range(start,end):
        face=tri[i]
        points=p[face]
        if apron and points[:,2].max()>102.35:continue
        slot=data["triangle_materials"][i]
        if name=="Soft collar stand with inner facing":slot=8
        if name=="Skived and rounded waist belt":slot=9
        if name=="Continuous linen shirt":
            mid=points.mean(0)
            if mid[1]>0 and mid[2]>138+1.15*abs(mid[0]):slot=8
        corners=[piece.corner(p[v],data["normals"][i][j],data["uv"][i][j],data["weights"][v]) for j,v in enumerate(face)]
        piece.face(corners,slot)

# Intersect the actual shirt triangles so the crossed bands follow the chest rather than hovering over it.
_,start,_,end=parts["Continuous linen shirt"]
faces=p[tri[start:end]]
xz=faces[:,:,[0,2]]
def shirt_front(x,z):
    a=xz[:,0];e=xz[:,1]-a;f=xz[:,2]-a;q=np.array([x,z])-a
    den=e[:,0]*f[:,1]-e[:,1]*f[:,0]
    den[np.abs(den)<1e-9]=np.nan
    u=(q[:,0]*f[:,1]-q[:,1]*f[:,0])/den
    v=(e[:,0]*q[:,1]-e[:,1]*q[:,0])/den
    hit=(u>=0)&(v>=0)&(u+v<=1)
    if hit.any():
        return np.max((faces[:,0,1]+u*(faces[:,1,1]-faces[:,0,1])+v*(faces[:,2,1]-faces[:,0,1]))[hit])
    idx=shirt[(np.abs(shirt[:,0]-x)<1.6)&(np.abs(shirt[:,2]-z)<1.8)]
    return idx[:,1].max() if len(idx) else 6.2

for side,bottom,layer in ([] if refined else [(1,133.0,.30),(-1,103.0,.66)]):
    # Wearer's left lapel crosses the inner band and tucks into the sash on the right.
    rows=[]
    for z in np.linspace(bottom,151.0,46):
        cx=np.interp(z,[103,132,151],[-12.0,0,6.5])*(-side)
        row=[]
        for offset in np.linspace(-1.85,1.85,6):
            x=cx+offset
            row.append([x,shirt_front(x,z)+layer+.16*(1-(offset/1.85)**2),z])
        rows.append(row)
    piece.grid(rows,bind,9,(.24,2))
    piece.tube(np.array(rows)[:,0,:],.115,7,bind,6)

# Short side-vented tails end at the upper thigh. The open front gives the split leather apron room to move.
for lo,hi in [(46,91),(92.5,267.5),(269,314)]:
    rows=[]
    for v in np.linspace(0,1,19):
        row=[]
        for deg in np.linspace(lo,hi,max(9,int((hi-lo)/3))):
            a=np.deg2rad(deg)
            z=77+26*v+2.2*abs(np.cos(a))*(1-v)
            radx=np.interp(z,[77,87,94,103],[23.7,22.4,20.8,16.7])
            rady=np.interp(z,[77,87,94,103],[19.2,19.3,18.7,14.2])
            ripple=.65*np.sin(9*a+.65*v)*(1-v)
            # Vent panels meet above the cut.
            if deg in (lo,hi) and 85<deg<275:
                a+=np.deg2rad((.8 if deg==hi else -.8)*min(v*2,1.))
            row.append([(radx+ripple)*np.sin(a),1+(rady+ripple)*np.cos(a),z])
        rows.append(row)
    piece.grid(rows,bind,0,(1.5*(hi-lo)/100,2.0))

# The marking rule and awl are carried against the apron beneath a stitched leather keeper.
def at_tool(x,z):
    return np.array([x,17.5-.036*(x+4)**2+.02*(98-z),z])
def bar(x,z0,z1,halfwidth,depth,slot):
    a=np.linspace(0,2*np.pi,9)
    rows=[[at_tool(x+halfwidth*np.sign(np.cos(t))*abs(np.cos(t))**.3,z)+[0,depth*np.sign(np.sin(t))*abs(np.sin(t))**.3,0] for t in a] for z in (z0,z0+.15,z1-.15,z1)]
    piece.grid(rows,bind,slot,radial=True)
    for row,flip in ((rows[0],True),(rows[-1],False)):
        ids=[piece.corner(v,[0,0,-1 if flip else 1],v[:2],bind(v)) for v in row[:-1]]
        for j in range(1,len(ids)-1):piece.face([ids[0],ids[j],ids[j+1]][::1 if flip else -1],slot)
if refined:
    apron_details(piece,data,args.review_fit)
else:
    bar(-10.5,83,101,1.10,.36,10)
    for z in np.arange(84,100,1):
        piece.tube([at_tool(-10.95,z)+[0,.42,0],at_tool(-10.5+(.55 if z%5==0 else .06),z)+[0,.42,0]],.045,11,bind,5)
    bar(-14.2,87,96,.62,.55,10)
    piece.tube([at_tool(-14.2,87),at_tool(-14.1,84)],.19,11,bind,8)
    for z in [94.4,96.7]:
        path=[at_tool(x,z)+[0,.87,0] for x in np.linspace(-15.5,-9.1,15)]
        piece.tube(path,.44,3,bind,8)
if refined:
    used=sorted(set(piece.m))
    remap={old:new for new,old in enumerate(used)}
    piece.m=[remap[i] for i in piece.m]
    materials=[materials[i] for i in used]
piece.save("Workwear",materials,output)

# Dye the authored linen while retaining its aligned weave normal and roughness.
weave=cv2.imread(str(SMITH/"FinishR2/BodyOutfit/Textures/T_Smith_Linen_BC.png"))
value=cv2.cvtColor(weave,cv2.COLOR_BGR2GRAY).astype(float)
grain=(value/np.median(value)).clip(.36,2.3)
dyes=[("Flax",(89,104,116))] if refined else [("Indigo",(46,43,38)),("Lapel",(57,49,42)),("Flax",(128,150,166))]
for slot,bgr in dyes:
    cv2.imwrite(str(output/("T_Artisan"+slot+".png")),np.uint8(np.clip(grain[:,:,None]*bgr,0,255)))
