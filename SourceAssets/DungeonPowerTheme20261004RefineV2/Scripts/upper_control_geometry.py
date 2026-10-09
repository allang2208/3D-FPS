"""Solid envelope and platform extension, no hidden wall behind the glass."""
import math

def clip(poly,axis,value,greater):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[axis]-value)*(1 if greater else -1);db=(b[axis]-value)*(1 if greater else -1)
        if da>=0:result.append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db);result.append(tuple(a[k]+t*(b[k]-a[k]) for k in range(2)))
    return result

def platform(g,s,ri,z,ibeam):
    # The fill terminates on the exact 96-sided annulus boundary, without
    # overlapping deck caps or a convex hull closing the central hall.
    poly=[(ri*math.cos(i*math.tau/96),ri*math.sin(i*math.tau/96)) for i in range(96)]
    for axis,value,greater in ((0,-10,True),(0,10,False),(1,11.1,True)):
        poly=clip(poly,axis,value,greater)
    g.prism('GalleryDeck',poly,z-.24,z,'Deck',True)
    # End rails meet the existing inner rail, leaving a 2.04m clear balcony.
    end=math.sqrt((ri+.04)**2-10**2)
    for a,b in [((-10,end,z),(-10,11.1,z)),((-10,11.1,z),(10,11.1,z)),((10,11.1,z),(10,end,z))]:g.rail(a,b)
    for x in (-9,9):
        for y in (11.65,15):
            g.box('Structure',(x,y,(z-.56)/2),(.26,.32,z-.56),'Paint',collision=True)
            g.box('Trim',(x,y,.05),(.52,.58,.1),'Steel')
            for dx in (-.18,.18):
                for dy in (-.2,.2):g.bolt('Hardware',(x+dx,y+dy,.108),(0,0,1),.027)
        ibeam((x,11.35,z-.42),(x,19,z-.42),.28,.34)
    for y in (11.65,13.3,15,16.8):ibeam((-9.4,y,z-.40),(9.4,y,z-.40),.30,.30)

def cabin(g,s,atlas):
    room=s['control_room'];x0,x1=room['x_bounds_m'];front,back=room['y_bounds_m']
    z=room['floor_m'];h=room['height_m'];width=x1-x0
    def box(center,size,mat='Paint',collision=True):
        g.box('ControlRoom',(center[0],center[1],z+center[2]),size,mat,collision=collision)
    # Back closes between the sides; all visible skins occupy distinct planes.
    box((0,back,h/2),(width+.22,.22,h),'Concrete')
    box((0,(front+back)/2,h+.11),(width+.22,back-front+.22,.22),'Concrete')
    box((0,front,.44),(width-.06,.22,.88),'Concrete')
    box((0,front,.91),(width+.12,.28,.06),'Steel')
    box((0,front,3.035),(width+.12,.20,.15))
    box((0,front,3.415),(width+.22,.24,.61))
    # Four broad 3.92 x 2.00m independent safety-glass panes. The native
    # breakable components are installed separately into these real openings.
    for x in (-8,-4,0,4,8):box((x,front,1.98),(.06,.16,2.08),'Steel')
    for side,x in ((-1,x0),(1,x1)):
        # Side return glazing ends at the door jamb, no extra wall cap behind it.
        box((x,(front+16.08)/2,.44),(.22,16.08-front,.88),'Concrete')
        box((x,(front+16.115)/2,.91),(.28,16.115-front,.06),'Steel')
        box((x,(front+16.115)/2,3.08),(.20,16.115-front,.24))
        box((x,(front+back)/2,3.30),(.22,back-front,.20),'Concrete')
        for y in (16.115,18.485):box((x,y,1.225),(.26,.07,2.45),'Steel')
        box((x,17.3,2.465),(.26,2.44,.07),'Steel')
        box((x,17.3,2.85),(.22,2.44,.70),'Concrete')
        box((x,(18.52+back)/2,1.60),(.22,back-18.52,3.20),'Concrete')
        box((x,16.115,2.835),(.20,.07,.73),'Steel')
        # Seals are recessed to the door plane; there is no raised threshold.
        for y in (16.157,18.443):box((x+.027,y,1.21),(.026,.014,2.40),'Rubber',False)
        g.plate((x-side*.154,17.3,z+2.88),1.35,.30,'Exit',(-side,0,0),atlas)
        for y in (16.115,18.485):
            for zz in (.15,1.23,2.30):g.bolt('Hardware',(x+side*.139,y,z+zz),(side,0,0),.009)
    # Skirting and vents sit off the actual wall, not on duplicate wall skins.
    box((0,back-.126,.085),(width-.22,.026,.17),'Steel',False)
    for x in (-4.8,0,4.8):
        for j in range(13):box((x+(j-6)*.115,back-.137,2.70),(.052,.035,.27),'Steel',False)
    for x in (x0+.40,x1-.40):g.tray((x,front+.32),(x,back-.22),z+h-.31,.28)
    g.plate((0,front-.148,z+3.39),3.80,.62,'ControlRoom',(0,-1,0),atlas)
