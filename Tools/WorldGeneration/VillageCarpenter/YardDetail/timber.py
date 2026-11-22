"""Stock is seasoned on stickers, and separated by usable length and stage of milling."""
import random

def seasoning(mesh):
    rng=random.Random(40922)
    put=lambda *a,**k:mesh.board(rng,*a,**k)
    for x in (-88,0,88):
        put((x,0,6.5),88,16,13,90,'Oak',.65)
    z=13.
    for tier,count in enumerate((4,4,4,4,3,3)):
        thick=(5.3,4.3,5.1,3.7,4.1,3.4)[tier]
        widths=[rng.uniform(15.8,19.7) for _ in range(count)]
        y=-(sum(widths)+(count-1)*1.4)*.5 + (1.8 if tier%2 else -.6)
        for j,w in enumerate(widths):
            length=rng.uniform(223,265)-(tier*2 if tier>3 else 0)
            put((rng.uniform(-6.6,7.8),y+w*.5,z+thick*.5),length,w,thick,
                rng.uniform(-.38,.38),'Oak' if tier==1 and j==2 else 'Sawn',
                rng.uniform(.8,2.9) if j in (0,count-1) else .42,(tier+j)%3==0)
            y+=w+1.4
        z+=thick
        if tier<5:
            for x in (-88,0,88):
                put((x+rng.uniform(-1.1,1.1),0,z+1.55),82,5.5,3.1,90+rng.uniform(-.9,.9),'Oak',.19)
            z+=3.1

def flitches(mesh):
    rng=random.Random(11517)
    put=lambda *a,**k:mesh.board(rng,*a,**k)
    for x in (-72,70):
        put((x,0,4.5),96,14,9,90,'Oak',1.)
    z=9
    # Through-sawn exterior slabs retain a wane and a strip of bark at the edge.
    for tier,(widths,height) in enumerate([((29,25,26),13),((36,32),10.4),((27,32),9.2),((39,),7.1)]):
        y=-(sum(widths)+(len(widths)-1)*1.9)*.5+(-4,3,6,-4)[tier]
        for j,w in enumerate(widths):
            put((rng.uniform(-8,9),y+w/2,z+height/2),rng.uniform(176,222),w,height,
                rng.uniform(-.85,.85),'Sawn' if (tier+j)%3 else 'Oak',
                min(height*.86,rng.uniform(5,9)),(tier+j)%2==0)
            y+=w+1.9
        z+=height
    # A short offcut rests on the topmost slab, its end projecting a little.
    put((31,-4,z+1.9),88,17.5,3.8,-3.8,'Sawn',1.1,True)
    for x,y in ((-73,43),(70,-43)):
        put((x,y,1.9),15,6.4,3.8,9,'Oak',.66)

def crib(mesh):
    rng=random.Random(59373)
    put=lambda *a,**k:mesh.board(rng,*a,**k)
    # A low open-front crib with fixed cheeks and a clear view of the end stock.
    for x in (-35,35):
        put((x,0,3.2),67,9,6.4,90,'Oak',.7)
    for y in (-22,0,22):
        put((0,y,8.2),96,21,3.6,0,'Oak',.46)
    for x in (-45,45):
        for y in (-24,23):
            put((x,y,21.8),24,4.6,5.6,0,'Oak',.25,False,90)
        for z in (14,27):
            put((x,0,z),55,4.3,6,90,'Oak',.59)
    for z in (14,28):
        put((0,26,z),93,5.3,6,0,'Oak',.48)
    for tier,wlist in enumerate(((13.6,14.4,13.1),(15.2,12.8,12.6),(11.1,12.7))):
        y=-21.5
        thick=4.
        for j,w in enumerate(wlist):
            # Mixed cut lengths are pushed toward one cheek, leaving an irregular free end.
            length=rng.uniform(41,77)
            put((-38+length/2+rng.uniform(0,3),y+w/2,12+tier*thick),length,w,thick,
                rng.uniform(-1.7,1.7),'Oak' if (tier+j)%4==0 else 'Sawn',rng.uniform(.42,1.7),True)
            y+=w+1.3
    put((-12,-7,24.),44,8.5,4.,3.7,'Sawn',1.1,True)
    for i,(x,y,angle,l) in enumerate(((27,-34,11,23),(-21,-38,-8,31),(-5,-37,-15,15))):
        put((x,y,1.15),l,4+i*.6,2.3,angle,'Sawn',.9,True)
