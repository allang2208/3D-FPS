"""Inn joinery, in shell-local centimetres. Rear is +Y; all door sizes match the gameplay leaves."""
import math
from shell_geometry import Mesh,skin
from hall_plan import GUEST_ROWS,WEST_ROOM
from inn_geometry import cut_wall,FRONT,BACK,EAST,WEST,GUEST,OWNER

SUITE_X,SUITE_Y,SUITE_DOOR=92,292,286

def light_frame(m,axis,line,center,half,bottom,top,depth,stock=4.5):
    # The through mullion owns the crossing. Both cross rails end against its sides.
    left,right=center-half,center+half
    def rail(a,b,z0,z1,thick,mat='Oak'):
        skin(m,axis,line,a,b,z0,z1,mat,thick,bevel=.25)
    rail(left,right,bottom,bottom+stock,depth+5)
    rail(left,right,top-stock,top,depth+1)
    for a,b in [(left,left+stock),(right-stock,right)]:
        rail(a,b,bottom+stock+.02,top-stock-.02,depth)
    rail(center-2.1,center+2.1,bottom+stock+.02,top-stock-.02,depth*.56)
    z=bottom+(top-bottom)*.66
    for a,b in [(left+stock+.02,center-2.12),(center+2.12,right-stock-.02)]:
        rail(a,b,z-2.1,z+2.1,depth*.53)

def facade(wall,wood,axis,line,start,end,z0,z1,windows,front):
    holes=[(x-54,x+54,z0+92,z0+218) for x in windows]
    cut_wall(wall,axis,line,start,end,z0,z1,holes,'Masonry',27)
    point=lambda a,z:(a,line,z) if axis=='X' else (line,a,z)
    for z in (z0+7,z1-7):
        # No second plate over the continuous first-storey bressummer.
        if z0==-8 and z==z1-7:continue
        wood.timber('DarkWood',point(start,z),point(end,z),24,13)
    for x in windows:
        light_frame(wood,axis,line,x,53.97,z0+92.03,z0+217.97,27,5.2)

def panelling(m,axis,line,a,b,z0,z1,openings=(),depth=12):
    """Recessed field boards and proud rails, with the openings cut through every layer."""
    levels=sorted({z0,z1,*[v for _,_,lo,hi in openings for v in (lo,hi) if z0<v<z1]})
    for lo,hi in zip(levels,levels[1:]):
        cursor=a
        for left,right in sorted((max(a,x),min(b,y)) for x,y,low,high in openings if low<hi and high>lo and x<b and a<y)+[(b,b)]:
            if left>cursor+.1:
                # Vertical boards follow a fixed grid across the window and door heads.
                start=cursor
                while start<left-.08:
                    end=min(left, (math.floor((start+.01)/18)+1)*18)
                    if end-start>.08:skin(m,axis,line,start+.025,end-.025,lo+.025,hi-.025,'Oak',depth,bevel=.19)
                    start=end
                rails=[(z0,z0+10),(z0+78,z0+83),(z1-11,z1)]
                for low,high in rails:
                    low,high=max(lo,low),min(hi,high)
                    if high>low+.08:skin(m,axis,line,cursor+.04,left-.04,low+.04,high-.04,'DarkWood',depth+2.8,bevel=.28)
                for i in range(math.ceil((cursor+4)/92),math.floor((left-4)/92)+1):
                    for low,high in [(z0+10,z0+78),(z0+83,z1-11)]:
                        low,high=max(low,lo),min(high,hi)
                        if high>low+.08:skin(m,axis,line,92*i-2.5,92*i+2.5,low+.04,high-.04,'Sawn',depth+1.4,bevel=.25)
            cursor=max(cursor,right)
    for x,y,lo,hi in openings:
        if lo>z0+.1:continue
        for p in (x-3.2,y+3.2):skin(m,axis,line,p-3.1,p+3.1,z0,hi,'DarkWood',depth+3.9,bevel=.4)
        skin(m,axis,line,x-6.3,y+6.3,hi+.05,hi+5.5,'DarkWood',depth+4.3,bevel=.45)

def rooms(m):
    for y,yaw,split,xs in GUEST_ROWS:
        ends=[(WEST_ROOM,548),(614,EAST-23)] if yaw<0 else [(WEST_ROOM,EAST-23)]
        for a,b in ends:
            gates=[(x-55,x+55,GUEST,GUEST+221) for x in xs if a<x<b]
            panelling(m,'X',y,a,b,GUEST,OWNER-13,gates)
        near,far=(FRONT+25,y-7) if yaw<0 else (y+7,BACK-25)
        for x in (WEST_ROOM,split):panelling(m,'Y',x,near,far,GUEST,OWNER-13)
    # The rooms' outside walls retain masonry on the street and joinery on the room side.
    for axis,line,a,b,windows in [('X',FRONT+28,WEST_ROOM,EAST-28,[-138,320,525]),
            ('X',BACK-28,WEST_ROOM,EAST-28,[-115,300,504]),('Y',EAST-28,FRONT+31,81,[-240]),
            ('Y',EAST-28,319,BACK-31,[633]),('Y',EAST-28,96,305,[244])]:
        holes=[(x-57,x+57,GUEST+88,GUEST+222) for x in windows]
        panelling(m,axis,line,a,b,GUEST,OWNER-13,holes,4)
        for l,h,lo,hi in holes:
            # Return liners bridge the masonry reveal. Sills stop short of the original frames.
            sign=1 if line==FRONT+28 else -1
            mid=line-sign*10.4
            skin(m,axis,mid,l,h,lo-.5,lo+1.1,'Sawn',20.2)
            for edge in (l,h):skin(m,axis,mid,edge-.6,edge+.6,lo+1.13,hi-.03,'Oak',20.2)
    # A low, boarded inner ceiling closes the sleeping chamber beneath the sloping roof.
    panelling(m,'X',SUITE_Y,SUITE_X,EAST-16,OWNER,872,[(SUITE_DOOR-55,SUITE_DOOR+55,OWNER,OWNER+221)])
    panelling(m,'Y',SUITE_X,SUITE_Y+6.2,BACK-18,OWNER,872)
    bedroom_ceiling(m)

def bedroom_ceiling(m):
    for i in range(23):
        a=SUITE_Y+6+i*22.48
        m.box('Oak',SUITE_X+6,EAST-16,a,a+22.43,868,871)
    for y in (377,543,719):m.box('DarkWood',SUITE_X+6,EAST-17,y-4,y+4,861,867.96,.55)

def kitchen():
    m=Mesh()
    # Each sill replaces a strip of plaster. The supporting wall ends below the board.
    areas=[('X',-65,327,630,[]),('Y',321,-65,332,[(24,184,111,218)]),
           ('X',338,99,327,[(155,299,101,214)]),('Y',93,332,804,[(491,635,-2,226)])]
    for axis,line,a,b,holes in areas:
        cut_wall(m,axis,line,a,b,-2,278,[(x,y,lo-6 if lo>0 else lo,hi+6) for x,y,lo,hi in holes],'Lime',11)
        skin(m,axis,line,a,b,278.04,290,'DarkWood',15.3,bevel=.48)
        for at in (a+4,b-4):skin(m,axis,line,at-3.9,at+3.9,-2,277.94,'DarkWood',16.8,bevel=.44)
        for x,y,lo,hi in holes:
            for at in (x-3.4,y+3.4):skin(m,axis,line,at-3.3,at+3.3,-2,277.94,'Oak',17.6,bevel=.42)
            skin(m,axis,line,x,y,hi+.04,hi+5.97,'DarkWood',17.1,bevel=.45)
            if lo<0:continue
            # A two-sided oak pass with an unbroken worktop, and two gallows brackets on the public face.
            if axis=='X':
                m.box('Oak',x-10,y+10,line-49,line+28,lo-5.95,lo,.9)
                for xx in (x+9,y-9):
                    m.timber('DarkWood',(xx,line-8,lo-36),(xx,line-41,lo-6.05),5.2,6)
            else:
                m.box('Oak',line-34,line+23,x-7,y+7,lo-5.95,lo,.7)
                for yy in (x+9,y-9):
                    m.timber('DarkWood',(line-8,yy,lo-29),(line-28,yy,lo-6.05),5.2,5.5)
    return m

def fixtures():
    cupboard,mirror,settle=Mesh(),Mesh(),Mesh()
    # Cupboard front is -Y. Doors, rails and latches have independent contact planes.
    cupboard.box('DarkWood',-62,62,-25,25,8,174,.8)
    for z in (1,169,175):cupboard.box('Oak',-65,65,-28,28,z,z+4.4,.9)
    for x in (-32,32):
        cupboard.box('Oak',x-29.5,x+29.5,-28,-25.1,13,167,.6)
        for z in (29,93,151):cupboard.box('Sawn',x-26,x+26,-29.3,-28.04,z,z+3.1,.32)
        for xx in (x-21,x+21):cupboard.box('DarkWood',xx-2,xx+2,-29.1,-28.04,33,92.8,.25)
        cupboard.box('Brass',x+(-1 if x>0 else 1)*22-1.3,x+(-1 if x>0 else 1)*22+1.3,-31,-28.07,80,89,.65)
    for x in (-55,55):
        for y in (-21,21):cupboard.box('DarkWood',x-5,x+5,y-4,y+4,0,9,.4)
    # A small arch-headed plate with an oak and brass surround. One visible reflective face.
    def arch(radius,foot,cy):
        return [(-radius,foot),(radius,foot)]+[(radius*math.cos(i*math.pi/16),cy+radius*math.sin(i*math.pi/16)) for i in range(17)]
    def plaque(r,foot,cy,y,depth,mat):
        mirror.prism(mat,[(x,y,z) for x,z in arch(r,foot,cy)],(0,depth,0))
    plaque(24,0,43,0,3.5,'Oak');plaque(21.3,2.8,43,-.85,.82,'Brass')
    plaque(19.9,4.3,43,-1.36,.48,'Mirror')
    # A backed oak settle, for the parlour rather than a second dining group.
    settle.box('Oak',-70,70,-24,21,42,47,.75)
    for x in (-60,60):
        for y in (-17,17):settle.box('DarkWood',x-3,x+3,y-3,y+3,0,41.98,.45)
        settle.box('DarkWood',x-3,x+3,16,23,47.03,101,.5)
        settle.box('Oak',x-3.65,x+3.65,-22,23,63,68,.42)
        settle.box('DarkWood',x-2.5,x+2.5,-20,-15,47.02,62.98,.35)
    for i in range(7):
        x=-51+i*17
        settle.box('Oak',x-8.3,x+8.3,17.5,21.5,47.03,91,.45)
    settle.box('DarkWood',-64,64,16.5,23.5,91.05,98,.48)
    native_frame=Mesh()
    light_frame(native_frame,'X',0,0,46.1,-60.45,60.46,11.8,4.9)
    return dict(WindowFrame=native_frame,KitchenPass=kitchen(),Cupboard=cupboard,Mirror=mirror,Settle=settle)
