"""Fitted structure of the armourer's shop. All dimensions are centimetres."""
from math import ceil
from pathlib import Path
from random import Random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'VillageBakery'))
from shell_geometry import Mesh, skin

EAVE = 630
BELT = 328
WALLS = (
    ('X', 0, -497, 497, [(-82,82,0,245), (-377,-185,103,238), (202,354,108,232),
                           (-321,-185,427,557), (171,307,427,557)]),
    ('X', 912, -497, 497, [(-103,45,432,554)]),
    ('Y', -487, 12, 900, [(86,214,108,229), (245,379,432,553), (625,759,432,553)]),
    ('Y', 487, 12, 900, [(48,160,145,252), (470,615,452,572)]),
)


def regions(start, end, openings, bottom, top):
    rough = [(a-8,b+8,c-7 if c else -22,d+10) for a,b,c,d in openings]
    levels = sorted({bottom,top,*[k for _,_,c,d in rough for k in (c,d) if bottom<k<top]})
    for z,h in zip(levels,levels[1:]):
        cursor = start
        for a,b in sorted((a,b) for a,b,c,d in rough if c<h and d>z) + [(end,end)]:
            if a>cursor:
                yield cursor,a,z,h
            cursor = max(cursor,b)


def roof_z(x):
    return 912 - abs(x) * .57


def walls(body, timber, joinery):
    for axis,line,start,end,openings in WALLS:
        for bottom,top in ((-17,BELT),(BELT,EAVE)):
            for a,b,z,h in regions(start,end,openings,bottom,top):
                skin(body,axis,line,a,b,z,h,'Plaster',24)
                if bottom<BELT:
                    depth_direction=-1 if line<=0 else 1
                    skin(body,axis,line+12.2*depth_direction,a,b,z,h,'BedMortar',.8)
        for a,b,sill,head in openings:
            for lo,hi in ((a-8,a),(b,b+8)):
                skin(joinery,axis,line,lo,hi,sill,head,'Oak',36)
            skin(joinery,axis,line,a-8,b+8,head,head+10,'Oak',38)
            if sill:
                skin(joinery,axis,line,a-8,b+8,sill-7,sill,'Sawn',43,bevel=.8)
        # The sill and plate belong to the timber loft. The stone sales floor
        # below is uninterrupted along the display walls.
        for z in (BELT,EAVE-7):
            skin(timber,axis,line,start,end,z-7,z+7,'Oak',34,bevel=1)
        bays = [-482,-374,-101,25,121,369,482] if axis=='X' else [20,212,430,610,803,892]
        for p in bays:
            for a,b,z,h in regions(p-6,p+6,
                    [q for q in openings if q[1]+8>p-6 and q[0]-8<p+6],BELT+7,EAVE-14):
                # All posts in this list are clear of the openings except at a few jambs.
                a,b=max(p-6,a),min(p+6,b)
                if b>a:
                    skin(timber,axis,line,a,b,z,h,'Oak',31,bevel=.55)
        outside = -1 if line<=0 else 1
        off = line+outside*12.8
        def brace(a,b,z,h):
            pts = ((a,off,z),(b,off,h)) if axis=='X' else ((off,a,z),(off,b,h))
            timber.timber('Oak',*pts,9,11)
        if axis=='X':
            brace(-472,-385,BELT+17,442)
            brace(465,379,BELT+17,442)
        else:
            brace(32,190,BELT+18,583)
            brace(880,808,BELT+19,454)
    for y in (0,912):
        body.prism('Plaster',[(-487,y-10,EAVE),(487,y-10,EAVE),(0,y-10,roof_z(0)-8)],(0,20,0))
        for x in (-295,-145,0,145,295):
            timber.box('Oak',x-6,x+6,y-15,y+15,EAVE,roof_z(x)-8,.6)
        for s in (-1,1):
            timber.timber('Oak',(0,y,EAVE+9),(s*228,y,roof_z(228)-17),10,12)


def roof(mesh, frame):
    rng = Random(90344)
    extent = 540
    for s in (-1,1):
        def roof_panel(mat,xy,lift,thick):
            mesh.prism(mat,[(x,y,roof_z(x)+lift) for x,y in xy],(0,0,-thick))
        roof_panel('DarkWood',[(0,-44),(s*extent,-44),(s*extent,956),(0,956)],0,5)
        for row in range(20):
            x0 = row*27
            x1 = min(extent,x0+28)
            y=-44.
            while y<955.5:
                stop=min(956.,y+rng.uniform(23.,35.))
                if stop-y>1.:
                    clip=min(rng.uniform(1.2,2.8),(stop-y)*.18)
                    outline=[(s*x0,y+.16),(s*(x1-clip),y+.16),(s*x1,y+clip+.16),
                             (s*x1,stop-clip-.16),(s*(x1-clip),stop-.16),(s*x0,stop-.16)]
                    roof_panel('Slate',outline,2.15+(19-row)*.075+rng.uniform(0,.25),2.35)
                y=stop
        for x in (100,273,463):
            frame.timber('DarkWood',(s*x,-38,roof_z(x)-14),(s*x,949,roof_z(x)-14),14,15)
        for y in (-34,53,153,253,353,453,553,653,753,853,945):
            frame.timber('Oak',(s*534,y,roof_z(534)-8),(0,y,roof_z(0)-8),8,10)
        for y in (-40,952):
            frame.timber('Oak',(s*539,y,roof_z(539)-2),(0,y,912),11,15)
        frame.timber('DarkWood',(s*537,-44,roof_z(537)-6),(s*537,956,roof_z(537)-6),10,13)
        for y in range(-44,956,45):
            mesh.prism('Slate',[(0,y,910),(s*14,y,904),(s*13,y,912),(0,y,921)],(0,min(45.4,956-y),0))
    for y in (155,458,762):
        frame.timber('Oak',(-486,y,621),(486,y,621),16,18)
        frame.timber('Oak',(0,y,626),(0,y,897),15,15)
        for s in (-1,1):
            frame.timber('Oak',(s*16,y,646),(s*237,y,roof_z(237)-17),11,13)


def floor_and_stair(floor, frame, stair):
    rng=Random(91437)
    floor.box('Mortar',-475.5,475.5,-13,900,-15,-1.5)
    y=-13.
    while y<899.:
        stop=min(900.,y+rng.uniform(33,52))
        x=-475.5
        while x<475.:
            end=min(475.5,x+rng.uniform(47,92))
            if end-x>1.2 and stop-y>1.2:
                floor.box('Flags',x+.4,end-.4,y+.4,stop-.4,-2.8,0,1.)
            x=end
        y=stop
    floor.prism('Flags',[(-82,-62,-7),(-82,-62,-3.7),(-82,-12,0),(-82,-12,-7)],(164,0,0))
    stair_start, landing = 135.,720.
    cut_x=319.
    for a,b,c,d in ((-476,cut_x,11,901),(cut_x,476,11,stair_start),(cut_x,476,landing,901)):
        floor.box('DarkWood',a,b,c,d,331,335)
        x=a
        while x<b-.1:
            end=min(b,x+rng.uniform(19.,28.))
            y=c
            while y<d-.1:
                stop=min(d,y+rng.uniform(206,318))
                if end-x>.8 and stop-y>.8:
                    floor.box('Sawn',x+.1,end-.1,y+.12,stop-.12,334.8,340,.48)
                y=stop
            x=end
    for y in range(25,890,60):
        end=cut_x-5 if stair_start-8<y<landing+8 else 480
        frame.timber('Oak',(-481,y,322),(end,y,322),11,18)
    frame.timber('Oak',(cut_x-5,stair_start-7,322),(cut_x-5,landing+8,322),12,18)
    for y in (stair_start-7,landing+7):
        frame.timber('Oak',(cut_x-9,y,322),(479,y,322),12,18)
    n=20
    run=(landing-stair_start)/n
    for i in range(n):
        y=stair_start+i*run
        top=(i+1)*17.
        stair.box('Sawn',325,467,y-2.1,y+run,top-4.6,top,.85)
        stair.box('Oak',328,464,y,y+2.4,top-17.5,top-4.5,.3)
    for x in (333,459):
        stair.timber('Oak',(x,stair_start-3,-5),(x,landing+3,333),10,17)
        for i in range(0,n,3):
            y=stair_start+(i+.35)*run
            z=(i+1)*17
            stair.box('Oak',x-3.1,x+3.1,y-3.1,y+3.1,z-4,z+89,.7)
        for lift,width in ((101,6.4),(58,4)):
            stair.timber('Oak',(x,stair_start+2,lift),(x,landing-3,lift+336),width,width)
    # The upper guard ends at the head of the stairs; the rear landing
    # opens west across the whole house instead of ending in a railing.
    for j in range(12):
        y=stair_start+4+j*(landing-stair_start-8)/11
        stair.box('Oak',cut_x-9,cut_x-3,y-3,y+3,339,433,.6)
    for z,w in ((430,7),(379,4)):
        stair.timber('Oak',(cut_x-6,stair_start-4,z),(cut_x-6,landing-3,z),w,w)
        stair.timber('Oak',(cut_x-6,stair_start-4,z),(473,stair_start-4,z),w,w)
    for x in (365,410,459):
        stair.box('Oak',x-3,x+3,stair_start-7,stair_start-1,339,432,.7)


def storefront(mesh):
    # In-swing plank doors are pinned open against their internal jambs.
    for s in (-1,1):
        x=s*78
        for i in range(6):
            y=18+i*12.6
            mesh.box('Sawn',x-2.4,x+2.4,y,y+12.35,.5,239,.4)
        for z in (38,183):
            mesh.box('Iron',x-3.3,x+3.3,20,85,z,z+4.2,.5)
        mesh.timber('Oak',(x-s*3,24,46),(x-s*3,88,183),4.2,5.5)
    # A projecting slate pentice shelters only the threshold, leaving the wide
    # sales casements free to swing out towards the courtyard.
    for x in (-106,106):
        mesh.timber('Oak',(x,-13,254),(x,-72,280),9,8)
        mesh.timber('Oak',(x,-12,294),(x,-74,280),9,8)
    for side in (-1,1):
        mesh.timber('Oak',(side*117,-72,278),(side*117,-14,294),8,9)
    mesh.timber('Oak',(-118,-73,279),(118,-73,279),9,9)
    mesh.prism('DarkWood',[(-122,-80,282),(122,-80,282),(122,-9,301),(-122,-9,301)],(0,0,-3))
    for row in range(3):
        y=-80+row*24
        for i in range(8):
            x=-122+i*30.5
            mesh.prism('Slate',[(x+.2,y,283+row*6.35),(x+30.2,y,283+row*6.35),
                               (x+30.2,y+24.4,289.5+row*6.35),(x+.2,y+24.4,289.5+row*6.35)],(0,0,-1.4))

def models():
    parts={n: Mesh() for n in ('Envelope','Timber','Roof','Floors','Stair','StreetJoinery')}
    walls(parts['Envelope'],parts['Timber'],parts['StreetJoinery'])
    roof(parts['Roof'],parts['Timber'])
    floor_and_stair(parts['Floors'],parts['Timber'],parts['Stair'])
    storefront(parts['StreetJoinery'])
    return parts
