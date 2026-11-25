"""Three-storey inn, centimetres in the repaired house frame."""
from shell_geometry import Mesh,skin

WEST_ROOM=-328
AISLE=(88,312)
# Door centres; the east hinge opens into the room.
GUEST_ROWS=((88,-90,118,(-99,357)),(312,90,205,(-78,410)))
OWNER_DOOR=(-82,342)
def sockets(guest,owner):
    return [(y,x,guest,yaw) for y,yaw,_,xs in GUEST_ROWS for x in xs]+[(342,-82,owner,90)]

def partitions(m,timber,divider,front,back,east,guest,owner,eaves):
    for y,yaw,split,xs in GUEST_ROWS:
        near,far=(front+10,y) if yaw<0 else (y,back-13)
        if yaw<0:
            # Terminate the front cross wall against both faces of the existing chimney.
            divider(m,timber,'X',y,WEST_ROOM,548,guest,owner-13,xs)
            divider(m,timber,'X',y,614,east-10,guest,owner-13,[])
        else:
            divider(m,timber,'X',y,WEST_ROOM,east-10,guest,owner-13,xs)
        for x in (WEST_ROOM,split):
            divider(m,timber,'Y',x,near,far,guest,owner-13,[])
    # The private bedroom occupies the garden corner. Its side walls follow the low return roof.
    divider(m,timber,'X',342,WEST_ROOM,158,owner,eaves,[-82])
    for x in (WEST_ROOM,158):
        divider(m,timber,'Y',x,342,423,owner,eaves,[])
        divider(m,timber,'Y',x,423,back-13,owner,872,[])
        m.prism('Masonry',[(x-5,423,872),(x-5,423,958),(x-5,back-13,872)],(10,0,0))

def kitchen(cut):
    m=Mesh()
    # Keep the original firebox below its flue. A setback at the hatch frees a dining bay
    # in front of the prep room; staff reach the wash and pantry through the west return.
    walls=[('X',-65,321,630,[]),('Y',321,-65,338,[(24,184,111,218)]),
           ('X',338,93,321,[(155,299,101,214)]),('Y',93,338,804,[(491,635,-2,226)])]
    for axis,line,a,b,holes in walls:
        cut(m,axis,line,a,b,-2,286,holes,'Lime',11)
        skin(m,axis,line,a,b,278,290,'DarkWood',17)
        posts={a+5,b-5}
        for lo,hi,base,top in holes:
            posts.update((lo-4,hi+4))
            skin(m,axis,line,lo-6,hi+6,top,top+8,'DarkWood',17)
            if base>0:skin(m,axis,line,lo-6,hi+6,base-5,base,'Oak',39)
        for at in sorted(posts):skin(m,axis,line,at-4,at+4,-2,278,'Oak',16)
    return m
