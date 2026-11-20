"""Shared survey for the site drawing and the compacted-ground material mask."""
from pathlib import Path
import re
import sys
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"AbandonedVillage"))
from village_tread import soil_variation, tread
stations=np.array([list(map(float,r.split(","))) for r in re.findall(r"\{([\s\d,.-]+)\}",(root/"Source/FPSGAME/WorldGeneration/TemperateQuarryBanks.inl").read_text())])/100.
def ease(a,b,x):
    f=np.clip((x-a)/(b-a),0.,1.)
    return f*f*(3.-2.*f)
def section(y):
    i=np.clip(np.searchsorted(stations[:,0],y,side="right")-1,0,len(stations)-2)
    a,b=stations[i],stations[i+1]
    t=ease(a[...,0],b[...,0],y)
    return [a[...,k]+(b[...,k]-a[...,k])*t for k in range(1,7)]
def pad(x,y,cx,cy,rx,ry):
    return 1.-ease(.48,1.,((x-cx)/rx)**2+((y-cy)/ry)**2)
def line(x,y,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    p=np.clip(((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy),0,1)
    return np.hypot(x-a[0]-p*dx,y-a[1]-p*dy)
def verge_pockets():
    survey=root/"Source/FPSGAME/WorldGeneration/TemperateQuarryVerges.inl"
    for row in re.findall(r"\{([\s\d,.-]+)\}",survey.read_text()):
        cx,cy,rx,ry,heading,plants,gravel,groups=map(float,row.split(","))
        yield cx/100.,cy/100.,rx/100.,ry/100.,heading,plants,gravel,int(groups)

def rockfall_beds():
    # Start at the outer edge of the parent block, in the direction of the
    # corresponding native debris fan. The surveyed floor supplies the downhill tilt.
    path=root/"Source/FPSGAME/WorldGeneration/TemperateQuarryRockfalls.inl"
    for row in re.findall(r"^QUARRY_FALL\(([^)]+)\)",path.read_text(),re.M):
        values=row.split(',')
        cx,cy,sx,sy=(float(v)/100 for v in values[2:6])
        strike=np.deg2rad(float(values[7]))
        axis=np.array([float(v) for v in values[10:12]])
        axis/=np.linalg.norm(axis)
        along=np.array((np.cos(strike),np.sin(strike)))
        reach=.45*(sx*abs(along@axis)+sy*abs(along[0]*axis[1]-along[1]*axis[0]))
        toe=np.array([cx,cy])+axis*reach
        grade=(section(toe[1]+.25)[5]-section(toe[1]-.25)[5])/.50
        axis[1]-=.85*grade/np.sqrt(1+grade*grade)
        axis/=np.linalg.norm(axis)
        run=float(values[14])/100
        yield int(values[0]),toe,axis,run,int(values[13])

# Extents match the existing quarry projector. Each stone relief lives at its
# surveyed XY. It cannot repeat in rows where a track meets the scree.
def chip_detail(out,powder,pieces,allowed):
    n=2048
    px,py=70/n,92/n
    height=np.zeros((n,n),dtype='f')
    exposure=np.zeros_like(height)
    for x,y,length,width,angle,chip_height,tone,cut in pieces:
        ix=(x+35)/px-.5; iy=(y+40)/py-.5
        box=length/2+max(px,py)
        xx=np.arange(max(0,int(ix-box/px)),min(n,int(ix+box/px)+2))
        yy=np.arange(max(0,int(iy-box/py)),min(n,int(iy+box/py)+2))
        if not (xx.size and yy.size):continue
        dx=(xx[None,:]-ix)*px;dy=(yy[:,None]-iy)*py
        c,s=np.cos(angle),np.sin(angle)
        u=(dx*c+dy*s)*2/length;v=(dy*c-dx*s)*2/width
        # Flaky limestone shears into asymmetric straight edges with a narrow bevel.
        margin=np.minimum.reduce((1-abs(u),1-abs(v+.14*u),
                                  1.30-cut*u-.74*v,1.32+.83*u+.78*v))
        bevel=np.clip(margin/.32,0,1)
        surface=chip_height*bevel*(.82+.13*u+.05*v)
        coverage=np.clip(margin*min(width/py,length/px)*.62+.12,0,1)
        indices=np.s_[yy[0]:yy[-1]+1,xx[0]:xx[-1]+1]
        upper=surface>height[indices]
        np.copyto(exposure[indices],coverage*tone,where=upper)
        np.maximum(height[indices],surface,out=height[indices])
    def enlarge(field):
        return np.asarray(Image.fromarray(field.astype('f')).resize((n,n),Image.Resampling.BILINEAR))
    protection=enlarge(allowed)
    height*=protection
    dy,dx=np.gradient(height,py,px)
    data=np.stack((.5-.5*dx,.5-.5*dy,exposure*protection,enlarge(powder)),axis=-1)
    Image.fromarray(np.rint(np.clip(data,0,1)*255).astype('uint8')).save(out/"T_QuarryDressingSpalls.png")

def work_debris(x,y,macro,soil,grain,allowed):
    powder=np.zeros_like(x)
    gravel=np.zeros_like(x)
    pieces=[]
    def splinters(rng,center,bearing,extent,count,scale):
        tangent=np.array([np.cos(bearing),np.sin(bearing)])
        normal=np.array([-tangent[1],tangent[0]])
        for _ in range(count):
            xy=center+tangent*rng.normal(0,extent)+normal*rng.normal(0,.48*extent)
            length=rng.uniform(.09,.34)*scale
            width=length*rng.uniform(.35,.83)
            pieces.append((*xy,length,width,bearing+rng.normal(0,.68),
                           width*rng.uniform(.07,.18),rng.uniform(.46,.94),rng.uniform(.68,1.03)))
    for cut,toe,axis,run,chip_count in rockfall_beds():
        side=np.array([-axis[1],axis[0]])
        along=(x-toe[0])*axis[0]+(y-toe[1])*axis[1]
        across=(x-toe[0])*side[0]+(y-toe[1])*side[1]
        t=np.clip(along/run,0,1)
        # A second lobe catches finer material further from the break. It overlaps
        # the coarse deposit only at the neck; small sheltered pockets retain soil.
        coarse_width=.93+run*(.10+.16*t)
        coarse=(1-ease(.34,1.,abs(across+.44*np.sin(4*t+cut)+.34*soil)/coarse_width))
        coarse*=ease(-1.9,-.28,along)*(1-ease(.43*run,1.04*run,along))
        tail=across-(1 if cut%2 else -1)*(.44+.91*t)+.39*soil
        dust=(1-ease(.17,1.,abs(tail)/(.68+run*.16*t)))
        dust*=ease(-1.15,.05,along)*(1-ease(.66*run,1.22*run,along))
        powder=np.maximum(powder,(.34*coarse+.66*dust)*(.78+.22*macro+.14*grain))
        gravel=np.maximum(gravel,coarse*(.80+.17*soil))
        rng=np.random.default_rng(13061+cut)
        for j in range(13+chip_count//3):
            u=rng.uniform(-.12,1.02)
            root=toe+run*u*axis+side*rng.normal(0,.40+.67*max(u,0))
            splinters(rng,root,np.arctan2(axis[1],axis[0]),.18+.35*max(u,0),
                      rng.integers(5,14),1.46-.78*max(u,0))
    # Trimming fines under the bench spill past the stock. At the crane the
    # swing is swept clean; chips and older, duller fines gather at the two margins.
    sweeps=(
        ([(-15.6,-18.7,.81),(-14.4,-19.5,.61),(-12.0,-19.8,.33)],.91,32,.62),
        ([(7.6,-14.2,.62),(8.1,-13.0,.77),(9.8,-12.6,.48)],.71,21,.81),
        ([(11.6,-15.2,.56),(10.5,-16.1,.72),(8.4,-17.0,.33)],.62,19,.72))
    for i,(points,strength,count,scale) in enumerate(sweeps):
        sweep=ease(-.72,.38,tread(x,y,points,.16*soil)+.25*grain)
        powder=np.maximum(powder,strength*sweep*(.84+.18*soil))
        rng=np.random.default_rng(7131+i)
        for _ in range(count):
            j=rng.integers(len(points)-1)
            a,b=np.array(points[j][:2]),np.array(points[j+1][:2])
            root=a+(b-a)*rng.random()+rng.normal(0,.24,2)
            splinters(rng,root,np.arctan2(*(b-a)[::-1]),.20,rng.integers(3,9),scale)
    return np.clip(powder*allowed,0,1),gravel*allowed,pieces

def make_mask():
    n=768
    x,y=np.meshgrid(-35+(np.arange(n)+.5)*70/n,-40+(np.arange(n)+.5)*92/n)
    w,e,wh,eh,road,floor=section(y)
    macro=soil_variation(x,y,4.8,507)
    soil=soil_variation(x,y,1.34,803)
    grain=soil_variation(x,y,.38,224)
    mottling=.54*macro+.33*soil+.13*grain
    wheel=abs(x-road)
    marks=1-ease(.12,.58,abs(wheel-1.1))
    track=1-ease(1.85,3.8,wheel-.99*macro-.46*soil-.22*grain)
    pressure=(1-ease(.09,.51,abs(wheel-1.10-.12*soil)))*(.72+.21*macro+.07*grain)
    westspur=np.minimum(line(x,y,(section(-21.1)[4],-21.1),(-5.3,-18.7)),line(x,y,(-5.3,-18.7),(-12.6,-15.1)))
    eastspur=np.minimum(line(x,y,(section(-20.7)[4],-20.7),(5.2,-16.8)),line(x,y,(5.2,-16.8),(10.5,-14.3)))
    spur=1-ease(.95,2.6,np.minimum(westspur,eastspur)+.38*mottling)
    shed=pad(x,y,-12.6,-15.1,8.70,7.30);hoist=pad(x,y,10.5,-14.3,6.50,5.70)
    # The doorway and dressing bench have different approach widths. Keep the
    # yard outside them broken, including turf in the lee of the stock.
    foot=tread(x,y,[(-5.3,-18.7,1.1),(-8.3,-17.5,.80),(-10.,-17.,.94),
                    (-12.,-16.45,.59)],.15*soil)
    bench=tread(x,y,[(-9.6,-17.4,.76),(-11.9,-19.5,.57),(-14.9,-19.1,.84)],.10*soil)
    stepped=ease(-.69,.32,np.maximum(foot,bench)+.31*mottling)
    # The laden approach swings out below the jib, then terminates at the load.
    landing=tread(x,y,[(2.0,-18.4,1.48),(5.3,-16.7,1.78),(7.7,-15.2,2.05),
                        (9.4,-13.4,1.30)],.19*macro)
    swing=ease(-.75,.42,landing+.32*mottling)
    swale_dist=abs(x-road-5.60-.60*np.sin(y/4.6))
    swale_run=ease(-10.7,-6.9,y)*(1-ease(11.3,15.8,y))
    swale=swale_run*(1-ease(.18,.82,swale_dist))
    silt=swale_run*(1-ease(.13,.87,swale_dist+.19*grain))
    apron=np.maximum(.40*shed,.42*hoist)*(.76+.24*soil)
    depth=np.maximum(w-x,x-e)
    spoil=ease(-6.7,-1.,depth+.88*mottling)*(1-ease(.15,2.4,depth))
    turf=np.zeros_like(x); deposits=np.zeros_like(x)
    for cx,cy,rx,ry,heading,plants,gravel,_ in verge_pockets():
        dx,dy=x-cx,y-cy
        c,s=np.cos(np.deg2rad(heading)),np.sin(np.deg2rad(heading))
        u,v=(c*dx+s*dy)/rx,(-s*dx+c*dy)/ry
        lobe=1-ease(.30,1.21,np.hypot(u,v-.24*np.sin(3.*u))+.27*soil+.12*grain)
        turf=np.maximum(turf,lobe*plants)
        deposits=np.maximum(deposits,lobe*gravel)
    allowed=ease(2.55,3.65,wheel)*(1-.86*turf)*(1-.85*stepped)*(1-.83*silt)
    powder,fans,pieces=work_debris(x,y,macro,soil,grain,allowed)
    spoil=np.maximum(spoil,fans)
    centre=(1-ease(.28,.87,wheel))*ease(-.20,.66,macro+.5*soil)*(1-np.maximum(swing,stepped))
    coarse=np.clip(.20+.67*spoil+.60*deposits+.28*swing+.19*pressure-.28*silt
                   +.30*soil+.22*grain-.14*stepped,0,1)
    tire_soil=track*(.62+.34*pressure+.18*mottling)*(1-.51*centre)
    coverage=np.maximum.reduce([tire_soil,.63*spur,.88*stepped,.93*swing,apron,
                                .92*spoil,.77*deposits,.79*silt,.97*powder])*(1-.59*turf)*(ease(-39,-32,y)*(1-ease(41,51,y)))
    # Fourth channel carries compressed damp soil. It stops before the dry spoil peaks.
    damp=np.clip(.19+.58*pressure+.23*stepped+.35*swing+.54*silt+.22*macro-.32*spoil-.18*deposits,0,1)
    # Actual working floor height. It gates the decal on contact with the ground,
    # even if the camera sees a roof, a hanging rope, or the player above it.
    floor=(1-shed)*floor+shed*section(-15.1)[5];floor=(1-hoist)*floor+hoist*section(-14.3)[5]
    def bank(d,h):return h*(.49*ease(.65,3.2,d)+.38*ease(3.5,5.7,d)+.13*ease(6.5,8.6,d))
    cutback=2.45*ease(-10,-6.5,y)*(1-ease(9.5,13.,y))
    floor+=bank(w-x-cutback,wh)+bank(x-e,eh)
    floor+=ease(7,17.3,depth)*(.96*np.sin(y/6.5+x/8.1)+.49*np.sin(y/3.25-x/4.7))
    floor+=(-.04*marks-.11*swale+.09*np.sin(x/4.9+.65*np.sin(y/5.75))*np.sin(y/3.6)*ease(2.55,6.7,wheel))*(1-shed-hoist)
    arr=np.stack((np.clip(coverage,0,1),coarse,np.clip((floor+2)/24,0,1),damp),axis=-1)
    out=root/"SourceAssets/HillsQuarryCutYard/Approach";out.mkdir(parents=True,exist_ok=True)
    Image.fromarray(np.rint(255*arr).astype('uint8')).save(out/"T_QuarryWorkGround.png")
    chip_detail(out,powder,pieces,allowed)
if __name__=="__main__":make_mask()
