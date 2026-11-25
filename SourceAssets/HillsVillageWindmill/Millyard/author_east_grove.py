"""Plant the meadow pocket east of the mill cart track, in mill-local centimetres."""
import argparse
import json
import math
import random
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from author_yard_margins import OUT, PROJECT, house_paths, plot_geometry, rotate, wall_segments

# Ground projection of the marked outline in the mill's 83-degree overhead view.
POCKET = Polygon([(1957,368),(1735,345),(1179,449),(1094,410),(976,489),
                  (909,612),(906,821),(873,928),(800,1062),(633,1197),
                  (549,1291),(493,1400),(516,1466),(627,1518),(695,1521),
                  (966,1414),(1160,1300),(1511,995),(1898,534)])
TREES = [
    # Species, root, max crown width, target height, yaw, lower trunk radius.
    ('GroveBeech',1430,630,428,635,34,13),
    ('GroveAlder',1070,841,358,464,-67,10),
    ('GroveBeechYoung',822,1288,201,327,141,6.5),
    ('GroveYoungAlder',1710,473,145,222,81,4.5),
]
# Elliptical glades interleave. Flowers favour sunny lips, twigs the inner beds.
BEDS = [(1490,570,260,153,-22),(1283,779,273,151,-38),
        (1060,879,176,141,-67),(1052,1107,223,159,-39),
        (803,1317,222,106,-36),(620,1417,109,64,-7),
        (1658,488,164,85,-12)]
SURVEY = OUT/'MillEastGroveSurvey.npz'


def capture_ground(folder):
    samples = []
    for state in ('repaired','ruin'):
        values = np.loadtxt(folder/(state+'.csv'), delimiter=',', skiprows=1)
        names = (folder/(state+'-hits.txt')).read_text(encoding='utf-8-sig').splitlines()
        ground_ids = [i for i,name in enumerate(names)
                      if name.startswith('TemperateHillsWorld_') and '/DynamicMeshComponent_' in name]
        samples.append((values, np.isin(values[:,3],ground_ids)))
    (a,va),(b,vb) = samples
    if not np.array_equal(a[:,:2], b[:,:2]):
        raise ValueError('The two site surveys use different coordinates')
    xs,ys = np.unique(a[:,0]),np.unique(a[:,1])
    soil = np.where(va & vb & (abs(a[:,2]-b[:,2]) < 2), (a[:,2]+b[:,2])/2, np.nan)
    np.savez_compressed(SURVEY, x=xs, y=ys, ground=soil.reshape(len(ys),len(xs)).astype('float32'))


def protected_ground():
    source = PROJECT/'SourceAssets/TemperateHillsVillage'
    plan = json.loads((source/'layout.json').read_text(encoding='utf8'))
    kit = json.loads((source/'house-pieces.json').read_text(encoding='utf8'))
    site = next(h for h in plan['houses'] if h[0]=='05')
    shape = plot_geometry(site,kit[site[2]],plan)
    nx,ny = shape['normal']
    ox,oy = (shape['entry'][0]*100-376.5*nx,shape['entry'][1]*100-376.5*ny)
    yaw = math.degrees(math.atan2(ny,nx))-90
    def local(p):
        return rotate(p[0]*100-ox,p[1]*100-oy,-yaw)
    fixed = []
    for path,width in [(r['points'],r['width']) for r in plan['roads']]+house_paths(plan,kit):
        fixed.append(LineString([local(p) for p in path]).buffer(width*50+10))
    for part,half in wall_segments(plan):
        fixed.append(LineString([local(part[1:3]),local(part[3:5])]).buffer(half*100+10))
    for h in plan['houses']:
        b = plot_geometry(h,kit[h[2]],plan)
        cx,cy = local(b['center'])
        hx,hy = [v*100+12 for v in b['half']]
        corners = [rotate(x,y,b['angle']-yaw) for x,y in ((-hx,-hy),(-hx,hy),(hx,hy),(hx,-hy))]
        fixed.append(Polygon([(cx+dx,cy+dy) for dx,dy in corners]))
    fixed.append(LineString([(308,358),(427,440),(449,541),(345,681),(162,808),(-50,960)]).buffer(70))
    fixed.append(LineString([(0,370),(-10,554),(-30,715),(-90,950),(-173,1190),(-315,1590)]).buffer(105))
    return unary_union(fixed)


def generate():
    rng = random.Random(872005)
    data = np.load(SURVEY)
    xs,ys,ground = data['x'],data['y'],data['ground']
    def height(x,y):
        col = int(round((x-xs[0])/(xs[1]-xs[0])))
        row = int(round((y-ys[0])/(ys[1]-ys[0])))
        return float(ground[row,col])

    obstacles = protected_ground()
    grove = POCKET.difference(obstacles)
    previous = json.loads((OUT/'MillVergeLayout.json').read_text())['instances']
    hard = [(x,y,math.hypot(w,d)*.5) for role,x,y,_,w,d,_,_ in previous
            if role.startswith(('MarginHazel','MarginRock','Chip','TreadChip'))]
    trees,items,roots = [],[],[]
    for role,x,y,width,h,yaw,r in TREES:
        pt = Point(x,y)
        z = height(x,y)
        if not grove.contains(pt) or pt.distance(obstacles)<width*.5+30 or not math.isfinite(z):
            raise ValueError('Occupied tree site: '+role)
        trees.append([role,x,y,z-2.5,width,h,yaw,r])
        hard.append((x,y,r+16))

    def place(role,x,y,w,d,h,angle,burial,woody=False):
        radius = math.hypot(w,d)*.5
        pt = Point(x,y)
        if not grove.contains(pt) or grove.boundary.distance(pt)<radius+2:
            return False
        root = radius if woody else min(10.,w*.22)
        if any(math.hypot(x-a,y-b)<r+root for a,b,r in hard):
            return False
        if any(math.hypot(x-a,y-b)<r+root for a,b,r in roots):
            return False
        z = height(x,y)
        if not math.isfinite(z):
            return False
        items.append([role,*[round(v,2) for v in (x,y,z-burial,w,d,h,angle)]])
        (hard if woody else roots).append((x,y,root))
        return True

    def in_bed(bed):
        cx,cy,rx,ry,heading = bed
        angle,r = rng.uniform(0,math.tau),math.sqrt(rng.random())
        dx,dy = rotate(rx*r*math.cos(angle),ry*r*math.sin(angle),heading)
        return cx+dx,cy+dy,r

    for i,bed in enumerate(BEDS):
        for n in range(2 if i!=5 else 1):
            for _ in range(35):
                x,y,_ = in_bed(bed)
                w = rng.uniform(70,135) if n==0 else rng.uniform(51,85)
                if place('MarginHazel'+'ABCD'[(i+n)%4],x,y,w,w*.75,w*rng.uniform(.50,.76),
                         rng.uniform(-180,180),2.,True):
                    break
    for i,bed in enumerate(BEDS):
        for role in ('GroveTwig','GroveSmallTwig','GroveStone'):
            for _ in range(28):
                x,y,_ = in_bed(bed)
                twig = role!='GroveStone'
                w = rng.uniform(30,57) if twig else rng.uniform(29,54)
                d,h = (w*.28,w*.075) if twig else (w*.70,w*.42)
                if place(role,x,y,w,d,h,rng.uniform(-180,180),1.1 if twig else h*.33,True):
                    break
        for _ in range(200):
            x,y,r = in_bed(bed)
            if rng.random()>.85-.45*r:continue
            role = rng.choices(('GroveSoftGrass','MarginFescue','MarginStems','GroveHerb','GroveFlower'),
                               (38,26,11,18,7 if i in (0,3,4,5) else 2))[0]
            w = rng.uniform(24,62) if role!='GroveFlower' else rng.uniform(19,36)
            h = rng.uniform(15,35) if role in ('GroveFlower','MarginStems') else w*rng.uniform(.34,.62)
            place(role,x,y,w,w*rng.uniform(.60,.91),h,rng.uniform(-180,180),1.3)
    # Colonies on the sunlit side spread in overlapping, irregular fans.
    for bed in [(1370,607,114,58,18),(1160,982,127,67,-36),
                (880,1178,109,61,-17),(731,1380,103,56,8)]:
        for _ in range(46):
            x,y,r = in_bed(bed)
            flower = rng.random()<.68-.21*r
            w = rng.uniform(26,45)*(1-.22*r)
            role = 'GroveFlower' if flower else 'GroveSoftGrass'
            place(role,x,y,w,w*rng.uniform(.70,.98),rng.uniform(14,29)*(1-.24*r),
                  rng.uniform(-180,180),1.1)
    (OUT/'MillEastGrove.json').write_text(json.dumps(dict(trees=trees,instances=items),separators=(',',':')),encoding='utf8')
    from collections import Counter
    print('East grove:',len(trees),'trees;',dict(Counter(p[0] for p in items)))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--survey',type=Path)
    args=parser.parse_args()
    if args.survey:capture_ground(args.survey)
    generate()
