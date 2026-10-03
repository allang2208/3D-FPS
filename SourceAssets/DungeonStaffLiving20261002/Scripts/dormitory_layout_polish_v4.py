"""Parallel beds face the entrance; variable wall furniture stays in safe bays."""
import random

def make_layouts(cfg):
    rng=random.Random(202610024);rooms=[];previews=[];beds=[]
    for row,side in enumerate((-1,1)):
        for col,(x0,x1) in enumerate(((-14,-5),(-5,4),(4,14))):
            rid=str(101+row*3+col);cx=(x0+x1)/2
            def wall_x(wall,depth):return x0+.235+depth/2 if wall=='west' else x1-.235-depth/2
            def facing(wall):return 90 if wall=='west' else -90
            def pose(slot,proto,x,q,yaw,z=0):
                return dict(id=slot+'_'+rid,prototype=proto,position=[x,side*q,z],yaw_blender_deg=yaw,
                    position_cm=[x*100,-side*q*100,z*100],yaw_ue=-yaw)
            variants=[]
            for index,bank in enumerate(('west','east','west','east')):
                other='east' if bank=='west' else 'west';dy=rng.uniform(-.035,.035)
                bookwall=bank if index<2 else other;shelfwall=other if index<2 else bank
                deskq=7.30 if index%2 else 7.48;deskx=wall_x(other,.58)
                chairx=deskx+(.83 if other=='west' else -.83)
                items=[pose('Locker0','Locker',wall_x(bank,.55),3.27+dy,facing(bank)),
                    pose('Locker1','Locker',wall_x(bank,.55),4.18+dy,facing(bank)),
                    pose('Bookcase','Bookcase',wall_x(bookwall,.40),5.62+dy,facing(bookwall)),
                    pose('Bookshelf','Bookshelf',wall_x(shelfwall,.34),5.70-dy,facing(shelfwall)),
                    pose('Desk','Desk',deskx,deskq,facing(other)),
                    pose('Chair','Chair',chairx,deskq,facing(other)+180),
                    pose('Bedside0','Bedside',cx-2.07,9.20+dy,0 if side>0 else 180),
                    pose('Bedside1','Bedside',cx+2.07,9.20-dy,0 if side>0 else 180)]
                items[0]['id']='Locker_'+rid+'_0';items[1]['id']='Locker_'+rid+'_1'
                variants.append(dict(id=index,name=('储物靠西','储物靠东','书柜换侧','书架换侧')[index],placements=items))
            preview=(row*3+col)%4;previews.extend(variants[preview]['placements'])
            rooms.append(dict(id=rid,side=side,wall_axes_m=[x0,x1,side*2,side*10],
                fixed_bed_ids=['Bed_'+rid+'_0','Bed_'+rid+'_1'],variants=variants,preview_variant=preview))
            for i in range(2):
                beds.append(dict(id='Bed_'+rid+'_'+str(i),position=[cx+(-1.24 if i==0 else 1.24),side*8.53,0],
                    yaw_blender_deg=90 if side>0 else -90))
    return dict(version=4,rooms=rooms,seed=-1,preview_seed=202610024,beds_fixed=True,
        placement_method='parallel head-to-rear-wall beds; side-wall furniture anchors; 3.5cm mounting clearance'),previews,beds
