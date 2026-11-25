"""Author the windmill verge from the two surveyed site states and the village plan (cm)."""
import argparse
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, map_coordinates

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
OUT=HERE/'WorkDetails'
sys.path.insert(0,str(PROJECT/'Tools/WorldGeneration/AbandonedVillage'))
from layout_geometry import house_paths, plot_geometry, rotate, wall_segments
from earth_form import elevation

# Each lobe is (centre, two radii, heading, rock content). Lobes join along the
# fronts of the two verges, with breaks at the screen, cart and repair station.
BEDS=[
    (-816,563,200,103,72,.48),(-693,730,255,151,36,.28),(-488,772,169,83,-11,.48),
    (-652,984,323,183,67,.22),(-550,1194,214,103,77,.63),(-591,1408,200,105,112,.30),
    (657,262,226,103,75,.62),(784,481,221,108,78,.36),(701,701,259,190,-27,.33),
    (483,808,205,95,-37,.65),(585,938,299,169,-49,.28),(374,1070,241,138,-34,.49),
    (161,1210,211,109,-48,.41),(218,1430,228,157,68,.24),
    (-418,-574,247,77,6,.72),(-146,-505,197,99,14,.61),
    (598,-117,235,92,75,.57),(-687,-117,201,85,88,.40),
    (153,634,113,56,52,.85),(-690,323,152,78,7,.63)]
# Position and target spread of the principal shrubs and embedded stones.
GROUPS=[
    (-729,726,161),(-608,927,118),(-568,1180,99),(-604,1380,91),(-870,529,99),
    (683,665,157),(553,893,133),(328,1031,105),(169,1230,92),(263,1410,118),
    (645,265,107),(612,-90,107),(-161,-512,92),(-612,-169,79)]
BANKS=[(-669,814,20,(1.43,1.55,1.06)),(-558,1119,73,(1.09,1.33,.82)),
       (641,809,-34,(1.54,1.68,1.20)),(315,1101,-40,(1.22,1.38,.82)),
       (175,1370,58,(1.05,1.32,.64))]
# Shallow, exposed aggregate where loaded feet and the single wheel shed soft
# soil. The centre of each deposit stays traversable, at most 2.2 cm of relief.
TREAD_GRAVEL=[(-150,714,123,39,70),(137,698,103,31,-34),(264,774,103,35,-39),
              (-70,950,131,37,106),(-260,1154,118,39,117),(-257,1360,109,33,101),
              (457,592,75,29,119),(-406,550,91,27,4),(-126,-626,90,29,-8)]
# Bounds of the downward decal, in the tower frame. Keep its last pixels transparent.
X0,X1,Y0,Y1=-1100,1140,-800,1660
STEP=4
XS=np.arange(X0,X1+1,STEP,dtype=np.float32)[None,:]
YS=np.arange(Y0,Y1+1,STEP,dtype=np.float32)[:,None]
SHAPE=(YS.shape[0],XS.shape[1])


def distance_to_segment(a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    t=np.clip(((XS-a[0])*dx+(YS-a[1])*dy)/max(dx*dx+dy*dy,1.),0,1)
    return np.hypot(XS-(a[0]+t*dx),YS-(a[1]+t*dy))


def keep_clear():
    plan_dir=PROJECT/'SourceAssets/TemperateHillsVillage'
    plan=json.loads((plan_dir/'layout.json').read_text(encoding='utf8'))
    kit=json.loads((plan_dir/'house-pieces.json').read_text(encoding='utf8'))
    house=next(h for h in plan['houses'] if h[0]=='05')
    frame=plot_geometry(house,kit[house[2]],plan)
    nx,ny=frame['normal']
    origin=(frame['entry'][0]*100-376.5*nx,frame['entry'][1]*100-376.5*ny)
    yaw=math.degrees(math.atan2(ny,nx))-90
    def local(p):return rotate(p[0]*100-origin[0],p[1]*100-origin[1],-yaw)
    clearance=np.minimum(np.minimum(XS-X0,X1-XS),np.minimum(YS-Y0,Y1-YS))
    def lane(points,r):
        for a,b in zip(points,points[1:]):
            if max(a[0],b[0])+r<X0 or min(a[0],b[0])-r>X1 or max(a[1],b[1])+r<Y0 or min(a[1],b[1])-r>Y1:continue
            np.minimum(clearance,distance_to_segment(a,b)-r,out=clearance)
    def rect(c,hx,hy,ang):
        a=math.radians(ang)
        lx=np.abs((XS-c[0])*math.cos(a)+(YS-c[1])*math.sin(a))-hx
        ly=np.abs(-(XS-c[0])*math.sin(a)+(YS-c[1])*math.cos(a))-hy
        np.minimum(clearance,np.hypot(np.maximum(lx,0),np.maximum(ly,0))+np.minimum(np.maximum(lx,ly),0),out=clearance)
    for h in plan['houses']:
        shape=plot_geometry(h,kit[h[2]],plan)
        rect(local(shape['center']),shape['half'][0]*100+8,shape['half'][1]*100+8,shape['angle']-yaw)
    for points,w in [(r['points'],r['width']) for r in plan['roads']]+house_paths(plan,kit):
        lane(list(map(local,points)),w*50+5)
    for piece,half in wall_segments(plan):
        lane([local(piece[1:3]),local(piece[3:5])],half*100+6)
    # Manual working clearances include the fully open leaves, turn at the barrow,
    # both sides of the screening table and the crouching space at the spare stones.
    lane([(0,370),(-10,554),(-30,715),(-90,950),(-173,1190),(-315,1590)],105)
    lane([(308,358),(427,440),(449,541),(345,681),(162,808),(-50,960)],70)
    lane([(-668,492),(-476,515),(-287,515),(-130,531),(0,510)],54)
    for c,hx,hy,ang in [((-678,382),142,95,7),((-367,424),149,78,13),
                         ((320,360),104,57,-157),((440,269),67,47,-14),
                         ((-353,-463),129,57,-10),((175,413),58,48,0)]:
        rect(c,hx,hy,ang)
    return clearance


def survey_files(directory):
    layers=[]
    for tag in ('repaired','ruin'):
        a=np.loadtxt(directory/(tag+'.csv'),skiprows=1,delimiter=',')
        cols=len(np.unique(a[:,0]))
        z=a[:,2].reshape(-1,cols)
        hit=a[:,3].astype(int).reshape(z.shape)
        names=(directory/(tag+'-hits.txt')).read_text(encoding='utf-8-sig').splitlines()
        names_lower=[n.lower() for n in names]
        ground_ids=[i for i,n in enumerate(names_lower)
                    if n.startswith('temperatehillsworld_') and '/dynamicmeshcomponent_' in n]
        if not ground_ids:
            raise ValueError('Missing terrain in the survey: '+str(names[:14]))
        terrain=np.isin(hit,ground_ids)
        layers.append((z,terrain))
    z,valid=layers[0]
    z2,valid2=layers[1]
    both=valid&valid2&(np.abs(z-z2)<2)
    if not both.any():raise ValueError('No common soil in the survey')
    np.savez_compressed(OUT/'MillVergeSurvey.npz',ground=(np.where(both,(z+z2)*.5,-999)).astype(np.float32))


def field_from_raster(a):
    yi,xi=np.broadcast_arrays((YS-Y0)/20,(XS-X0)/20)
    return map_coordinates(a,[yi,xi],order=1,mode='nearest')


def noise(rng,w,h):
    grid=Image.fromarray(rng.integers(0,256,(h,w),dtype=np.uint8))
    return np.asarray(grid.resize(SHAPE[::-1],Image.Resampling.BICUBIC),dtype=np.float32)/255-.5


def generate():
    ground=np.load(OUT/'MillVergeSurvey.npz')['ground']
    valid=ground>-100
    nearest=distance_transform_edt(~valid,return_distances=False,return_indices=True)
    levels=field_from_raster(ground[tuple(nearest)])
    terrain_clearance=field_from_raster(distance_transform_edt(valid)*20)-15
    clearance=np.minimum(keep_clear(),terrain_clearance)
    rng=random.Random(81513)
    texture_rng=np.random.default_rng(6990)
    broad=noise(texture_rng,22,23)
    patch=noise(texture_rng,69,72)
    detail=noise(texture_rng,240,240)
    strength=np.zeros(SHAPE,np.float32)
    gravel=np.zeros_like(strength)
    for x,y,rx,ry,angle,stone in BEDS:
        angle=math.radians(angle)
        dx,dy=XS-x,YS-y
        u=(dx*math.cos(angle)+dy*math.sin(angle))/rx
        v=(-dx*math.sin(angle)+dy*math.cos(angle))/ry
        edge=np.clip(1.36-np.hypot(u,v)+broad*.52+patch*.25,0,1)
        weight=edge*edge*(3-2*edge)
        gravel=np.where(weight>strength,stone,gravel)
        strength=np.maximum(strength,weight)
    # Colour reaches the tread edge before any rooted object. Break the edge in
    # several scales so the sward and gravel taper into individual stems and pebbles.
    opacity=strength*np.clip((clearance+12+broad*38+patch*19)/35,0,1)
    opacity*=np.clip(.97+patch*.47+detail*.64,.48,1)
    mix=np.clip(gravel-.15+broad*.77+patch*.48+detail*.15,0,1)
    for x,y,rx,ry,angle in TREAD_GRAVEL:
        angle=math.radians(angle)
        dx,dy=XS-x,YS-y
        u=(dx*math.cos(angle)+dy*math.sin(angle))/rx
        v=(-dx*math.sin(angle)+dy*math.cos(angle))/ry
        grit=np.clip(1.14-np.hypot(u,v)+broad*.42+patch*.43+detail*.22,0,1)
        grit*=np.clip(terrain_clearance/31,0,1)
        mix=np.where(grit*.78>opacity,np.maximum(mix,.92),mix)
        opacity=np.maximum(opacity,grit*.78)
    rgb=np.dstack((opacity,mix,np.zeros_like(mix)))
    Image.fromarray((np.clip(rgb,0,1)*255+.5).astype(np.uint8)).resize(
        (1024,1024),Image.Resampling.BICUBIC).save(OUT/'MillVergeMask.png')

    def at(field,x,y):
        return field[int(np.clip(round((y-Y0)/STEP),0,SHAPE[0]-1)),int(np.clip(round((x-X0)/STEP),0,SHAPE[1]-1))]
    def available(x,y,r):
        return at(clearance,x,y)>=r+4 and at(strength,x,y)>.037

    banks=[]
    for x,y,ang,s in BANKS:
        for _ in range(70):
            # Check the complete bank outline, including its curved tips.
            rim=[rotate(p*s[0],q*s[1],ang) for p in (-126,-84,-42,0,42,84,126) for q in (-52,0,52)]
            if all(available(x+dx,y+dy,3) for dx,dy in rim):
                banks.append((x,y,ang,s,float(at(levels,x,y))))
                break
            x+=rng.uniform(-17,17)
            y+=rng.uniform(-13,13)

    def height(x,y):
        h=float(at(levels,x,y))
        for bx,by,ang,s,bz in banks:
            dx,dy=rotate(x-bx,y-by,-ang)
            h=max(h,bz+s[2]*elevation(dx/s[0],-dy/s[1],252,88,21,False))
        return h

    poses=[]
    occupied=[]
    def plant(role,x,y,w,d,h,heading,sink,kind):
        radius=math.hypot(w,d)*.5
        if not available(x,y,radius):return False
        # Broad exclusion around hard objects. Grass blades may brush adjacent
        # grass but their roots never share the centre of a boulder or shrub.
        footprint=radius*.55 if kind=='grass' else radius+1.0
        if any(math.hypot(x-px,y-py)<pr+footprint for px,py,pr in occupied):return False
        occupied.append((x,y,footprint))
        z=height(x,y)-sink
        poses.append([role,round(x,2),round(y,2),round(z,2),round(w,2),round(d,2),round(h,2),round(heading,2)])
        return True

    def near(cx,cy,r):
        a=rng.uniform(0,math.tau)
        s=math.sqrt(rng.random())*r
        return cx+math.cos(a)*s,cy+math.sin(a)*s

    for idx,(cx,cy,wide) in enumerate(GROUPS):
        for n in range(3):
            w=wide*(1 if n==0 else rng.uniform(.42,.70))
            for _ in range(100):
                x,y=near(cx,cy,96 if n==0 else 151)
                if plant('MarginHazel'+'ABCD'[(idx+n)%4],x,y,w,w*rng.uniform(.72,.96),
                         w*rng.uniform(.58,.94),rng.uniform(-180,180),2.5,'shrub'):break

    for idx,(cx,cy,wide) in enumerate(GROUPS):
        for n in range(4):
            w=rng.uniform(66,111) if n==0 else rng.uniform(31,64)
            d=w*rng.uniform(.54,.88)
            h=w*rng.uniform(.41,.65)
            for _ in range(95):
                x,y=near(cx,cy,169)
                if plant('MarginRock'+'ABC'[(idx+n)%3],x,y,w,d,h,rng.uniform(-180,180),h*.24,'stone'):break

    # Exposed gravel in interrupted strings, with fines around the larger stones.
    for cx,cy,rx,ry,a,k in BEDS:
        for _ in range(140):
            u,v=near(0,0,1)
            dx,dy=rotate(u*rx,v*ry,a)
            x,y=cx+dx,cy+dy
            if rng.random()>k*.67+.13:continue
            w=rng.uniform(5,33)*(1-.32*abs(v))
            h=w*rng.uniform(.28,.55)
            plant('Chip'+str(rng.randint(1,6)),x,y,w,w*rng.uniform(.58,.91),h,rng.uniform(-180,180),h*.36,'stone')
    grass=['MarginSedge','MarginBent','ShortGrass','MarginBroadleaf','TallGrass']
    for cx,cy,rx,ry,a,k in BEDS:
        for _ in range(235):
            u,v=near(0,0,1.12)
            dx,dy=rotate(u*rx,v*ry,a)
            x,y=cx+dx,cy+dy
            if rng.random()>at(strength,x,y)*1.25:continue
            idx=rng.choices(range(5),weights=(21,24,31,13,11))[0]
            w=rng.uniform(23,65) if idx!=3 else rng.uniform(20,41)
            h=w*rng.uniform(.53,.91) if idx in (0,4) else w*rng.uniform(.29,.51)
            plant(grass[idx],x,y,w,w*rng.uniform(.70,.98),h,rng.uniform(-180,180),1.2,'grass')
    for cx,cy,rx,ry,angle in TREAD_GRAVEL:
        for _ in range(17):
            u,v=near(0,0,1.)
            dx,dy=rotate(u*rx,v*ry,angle)
            x,y=cx+dx,cy+dy
            w=rng.uniform(6,28)*(1-.36*abs(v))
            d=w*rng.uniform(.48,.90)
            r=.5*math.hypot(w,d)
            if at(terrain_clearance,x,y)<r+5 or any(math.hypot(x-px,y-py)<pr+r for px,py,pr in occupied):
                continue
            h=rng.uniform(3.3,5.6)
            z=height(x,y)-h+rng.uniform(1.,2.2)
            occupied.append((x,y,r))
            poses.append(['TreadChip'+str(rng.randint(1,6)),round(x,2),round(y,2),round(z,2),
                          round(w,2),round(d,2),round(h,2),round(rng.uniform(-180,180),2)])
    # Low meadow colonies extend beyond the shrub crowns. Each tapers from
    # seed stems at its core to worn grass at the boundary with the footway.
    colonies=[(-825,575,143,87,66),(-731,708,188,115,31),(-487,714,165,71,-15),
              (-409,858,125,79,70),(-581,987,246,94,78),(-549,1197,181,118,60),
              (-657,1396,181,91,101),(-357,695,93,56,48),(717,372,154,83,79),
              (780,564,217,100,85),(800,798,163,95,-29),(618,895,230,119,-39),
              (417,1033,230,87,-37),(242,1173,164,106,-57),(194,1415,176,118,76),
              (901,1042,191,108,-66),(866,1204,137,76,97),(185,574,95,41,37),
              (-457,-578,135,56,9),(-169,-515,157,64,21),(618,-66,171,66,85)]
    fixed=[]
    for role,x,y,z,w,d,h,turn in poses:
        if role.startswith(('MarginRock','MarginHazel','Chip','TreadChip')):
            fixed.append((x,y,.5*math.hypot(w,d)))
    roots=[]
    for cx,cy,rx,ry,heading in colonies:
        for _ in range(190):
            u,v=near(0,0,1.)
            radial=math.hypot(u,v)
            dx,dy=rotate(u*rx,v*ry,heading)
            x,y=cx+dx,cy+dy
            if rng.random()>(1.-.64*radial):continue
            role=rng.choices(('MarginTuft','MarginFescue','MarginStems'),(5,4,1))[0]
            w=rng.uniform(29,58)*(1.-.2*radial)
            d=w*rng.uniform(.64,.91)
            radius=.5*math.hypot(w,d)
            if at(clearance,x,y)<radius+5:continue
            if any(math.hypot(x-px,y-py)<pr+radius for px,py,pr in fixed):continue
            if any(math.hypot(x-px,y-py)<pr+w*.22 for px,py,pr in roots):continue
            roots.append((x,y,w*.22))
            h=(rng.uniform(25,40) if role=='MarginStems' else rng.uniform(13,28))*(1.-.36*radial)
            poses.append([role,round(x,2),round(y,2),round(height(x,y)-1.2,2),
                          round(w,2),round(d,2),round(h,2),round(rng.uniform(-180,180),2)])
    output={'extent':[X0,X1,Y0,Y1],'banks':banks,'instances':poses}
    (OUT/'MillVergeLayout.json').write_text(json.dumps(output,separators=(',',':')),encoding='utf8')
    from collections import Counter
    print('banks',len(banks),'instances',len(poses),Counter(p[0] for p in poses))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--survey',type=Path)
    args=parser.parse_args()
    if args.survey:survey_files(args.survey)
    generate()
