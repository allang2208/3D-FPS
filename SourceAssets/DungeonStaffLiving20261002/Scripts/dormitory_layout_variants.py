"""Dimensioned safe wall anchors, four room plans and bounded authored offsets.
Beds are fixed. Furniture transforms are authored, not free runtime jitter.
"""
import random

def make_layouts(cfg):
    rng=random.Random(20261002)
    rooms=[]
    previews=[]
    descriptors=[]
    for row,side in enumerate((-1,1)):
        for col,(x0,x1) in enumerate(((-14,-5),(-5,4),(4,14))):
            room_id=str(101+row*3+col);cx=(x0+x1)/2
            # The inner finish is about 15.5cm from wall axis. Back panels keep
            # at least 3.5cm extra clearance; handles/opening sweeps face inward.
            def wall_x(wall,depth):
                return x0+.235+depth/2 if wall=='west' else x1-.235-depth/2
            def facing(wall):return 90 if wall=='west' else -90
            def pose(slot,prototype,x,q,yaw,z=0):
                return dict(id=slot+'_'+room_id,prototype=prototype,position=[x,side*q,z],yaw_blender_deg=yaw,
                    position_cm=[x*100,-side*q*100,z*100],yaw_ue=-yaw)
            variants=[]
            # Bookcase and shelf use alternate walls and exchange their position
            # along the side wall. Locker banks also change walls together.
            plans=[('west','west','east',0.,5.47,4.70),
                   ('east','east','west',-1.35,5.47,4.80),
                   ('west','east','west',1.35,4.82,5.47),
                   ('east','west','east',-.42,4.78,5.47)]
            for index,(bank,bookwall,shelfwall,desk_dx,bookq,shelfq) in enumerate(plans):
                dy=rng.uniform(-.035,.035)
                desk_x=cx+desk_dx+rng.uniform(-.10,.10)
                items=[pose('Locker0','Locker',wall_x(bank,.55),3.24+dy,facing(bank)),
                       pose('Locker1','Locker',wall_x(bank,.55),4.10+dy,facing(bank)),
                       pose('Bookcase','Bookcase',wall_x(bookwall,.40),bookq+rng.uniform(-.035,.035),facing(bookwall)),
                       pose('Bookshelf','Bookshelf',wall_x(shelfwall,.34),shelfq+rng.uniform(-.035,.035),facing(shelfwall)),
                       pose('Desk','Desk',desk_x,9.46,0 if side>0 else 180),
                       pose('Chair','Chair',desk_x,8.59,180 if side>0 else 0),
                       pose('Bedside0','Bedside',cx-1.03,7.12+dy,0 if side>0 else 180),
                       pose('Bedside1','Bedside',cx+3.87,7.18-dy,0 if side>0 else 180)]
                # Preserve the existing locker identities and panel storage keys.
                items[0]['id']='Locker_'+room_id+'_0';items[1]['id']='Locker_'+room_id+'_1'
                variants.append(dict(id=index,name=['书柜靠西','书柜靠东','双侧分置','储物靠东'][index],placements=items))
            preview=(row*3+col)%4
            previews.extend(variants[preview]['placements'])
            rooms.append(dict(id=room_id,side=side,wall_axes_m=[x0,x1,side*2,side*10],
                fixed_bed_ids=['Bed_'+room_id+'_0','Bed_'+room_id+'_1'],variants=variants,preview_variant=preview))
            for item in variants[preview]['placements']:
                if item['prototype'] in ('Bookcase','Bookshelf','Bedside'):
                    descriptors.append(dict(id=item['id'],prototype=item['prototype'],room_id='StaffDormitory',
                        bedroom_id=room_id,container_id='StaffDormitory.'+item['id']))
    return dict(version=2,rooms=rooms,seed=-1,preview_seed=20261002,
        placement_method='wall inner face + 3.5cm clearance + half depth; bounded authored longitudinal offset',
        beds_fixed=True),previews,descriptors
