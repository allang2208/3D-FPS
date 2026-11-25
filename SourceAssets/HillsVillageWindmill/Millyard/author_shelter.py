"""Tied flax sack, screening shade, stone sleepers and vented smoke hood."""
import math
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from author_work_tools import mesh, reset, rod, save, section
from mathutils import Vector

tau=math.tau


def cord(name,points,r,material='Rope',closed=False):
    points=[Vector(p) for p in points]
    verts,faces=[],[]
    for i,p in enumerate(points):
        prev=points[(i-1)%len(points)] if i or closed else p
        nxt=points[(i+1)%len(points)] if i+1<len(points) or closed else p
        direction=(nxt-prev).normalized()
        ref=Vector((0,0,1)) if abs(direction.z)<.94 else Vector((1,0,0))
        u=direction.cross(ref).normalized()
        v=direction.cross(u)
        verts.extend(p+r*(math.cos(j*tau/6)*u+math.sin(j*tau/6)*v) for j in range(6))
        if closed or i+1<len(points):
            k=(i+1)%len(points)
            faces.extend((6*i+j,6*i+(j+1)%6,6*k+(j+1)%6,6*k+j) for j in range(6))
    mesh(name,verts,faces,material)


def sack():
    reset()
    profile=[(0,13.5),(.7,15.4),(2,17.8),(4,19.0),(9,20.2),(18,20.5),
        (27,19.8),(33,18.7),(38,16.4),(42,13.1),(45,8.1),(47,5.0),(48.5,4.1),
        (50,4.4),(52,6.2),(54.5,7.5),(56,7.8)]
    rows=[]
    for (a,ra),(b,rb) in zip(profile,profile[1:]):
        n=math.ceil((b-a)/1.5)
        rows.extend((a+(b-a)*i/n,ra+(rb-ra)*i/n) for i in range(n))
    rows.append(profile[-1])
    verts,faces=[],[]
    count=96
    def cloth(z,rad,a):
        shoulder=math.exp(-((z-44)/9)**2)
        hem=math.exp(-((z-54)/4)**2)
        low=math.exp(-((z-6)/6)**2)
        pleat=(.44+1.15*shoulder+.85*hem)*math.sin(9*a+.035*z+.54*math.sin(3*a+.07*z))
        wrinkle=.78*math.sin(3*a+.094*z)+.42*math.cos(5*a-.14*z)
        radius=rad+pleat+wrinkle+low*1.08*math.sin(5*a+.48*z)
        return (-.045*z+.48*math.sin(.09*z)+radius*math.cos(a),
                .032*z+.82*radius*math.sin(a),
                z+hem*(1.65*math.sin(4*a)+.74*math.cos(7*a)))
    for i,(z,r) in enumerate(rows):
        for j in range(count):
            verts.append(cloth(z,r,j*tau/count))
            if i+1<len(rows):
                k=(j+1)%count
                faces.append((i*count+j,i*count+k,(i+1)*count+k,(i+1)*count+j))
    faces.append(tuple(reversed(range(count))))
    start=len(verts)-count
    for j in range(count):
        x,y,z=verts[start+j]
        verts.append((x*.75-.4,y*.75+.3,z-4.2))
    for j in range(count):
        k=(j+1)%count
        faces.append((start+j,start+k,start+count+k,start+count+j))
    faces.append(tuple(range(start+count,start+2*count)))
    ob=mesh('Worn flax bag',verts,faces,'Flax')
    for p in ob.data.polygons:
        p.use_smooth=True
    for z in (48,48.8):
        points=[cloth(z,4.64,j*tau/64) for j in range(64)]
        cord('Double neck binding',points,.44,closed=True)
    x,y,z=cloth(48.3,4.7,-.9)
    cord('Loose knotted end',[(x,y,z),(x+1,y-1,z+.5),(x+2,y-.7,z+.2),
         (x+2.4,y-2.1,z-.6),(x+4.1,y-3,z-2.8),(x+5.9,y-3.8,z-7.0)],.36)
    for i in range(1,len(rows)-5,2):
        a=.74+.018*math.sin(i*.35)
        p=Vector(cloth(*rows[i],a))
        q=Vector(cloth(*rows[i+1],a+.027))
        off=Vector((.26,.19,0))
        cord('Hand sewn side stitch',[p+off,q+off],.16,'Rope')
    save('TiedSack')


def shade():
    reset()
    for x in (-94,94):
        for y in (-51,51):
            z=219 if y<0 else 199
            rod('Cleft upright',(x*.98,y*1.02,-.5),(x,y,z+2.0),3.7,2.75,'Oak',9)
        rod('Pitched side rail',(x,-56,219),(x,56,199),3.25,2.75,'Oak',9)
        rod('Rear knee brace',(x,-51,168),(x,-10,209),2.1,2.55,'Oak',9)
    for y,z in [(-51,219),(51,199)]:
        rod('Eave pole',(-100,y,z),(100,y,z),3.0,3.2,'Oak',10)
        for x in (-94,94):
            for j in range(3):
                cord('Cross lashing',[(x-4.1,y-3.8,z+j*.7-2.9),(x+3.5,y-3.1,z+j*.7+2),
                    (x+4.1,y+3.8,z+j*.7+2.1),(x-3.5,y+3.8,z+j*.7-2.1)],.43,closed=True)
    nx,ny=48,24
    def fabric(s,t):
        sag=(1-s*s)*(2.2+3.4*(1-t*t))
        y=55*t+.9*math.cos(3.4*s+3*t)*(1-s*s)
        z=212.4-10*t-sag+1.2*math.cos(s*13.5+t*.7)*(1-.5*abs(t))
        return (98*s,y,z)
    verts=[fabric(i*2/nx-1,j*2/ny-1) for i in range(nx+1) for j in range(ny+1)]
    faces=[]
    for i in range(nx):
        for j in range(ny):
            q=i*(ny+1)+j
            faces.append((q,q+ny+1,q+ny+2,q+1))
    ob=mesh('Two joined widths of flax cloth',verts,faces,'Canvas')
    for p in ob.data.polygons:p.use_smooth=True
    for t in (-1,1):
        cord('Rolled hem',[fabric(i/24-1,t) for i in range(49)],.51,'Flax')
    cord('Overlapping centre seam',[Vector(fabric(.06,j/12-1))+Vector((0,0,.22)) for j in range(25)],.34,'Flax')
    save('SortingShade')


def sleeper():
    reset()
    verts,faces=[],[]
    profile=[(-.48,.04),(-.37,0),(.34,0),(.48,.13),(.5,.78),(.35,.99),(-.38,1),(-.50,.81)]
    for i,x in enumerate((-48,-44,-12,19,45,48)):
        for j,(y,z) in enumerate(profile):
            verts.append((x+(.86*math.sin(j*2+i) if i in (0,5) else 0),
                13*y+.4*math.sin(i*.85+j),11*z+.38*math.cos(j*1.8+i)))
    for i in range(5):
        for j in range(8):
            k=(j+1)%8
            faces.append((i*8+j,i*8+k,(i+1)*8+k,(i+1)*8+j))
    faces.extend((tuple(reversed(range(8))),tuple(range(40,48))))
    mesh('Hand split bearer',verts,faces,'Oak')
    save('OakSkid')


def hood():
    reset()
    section('Rolled smoke hood',[(1.65,6.2),(2.8,6.4),(8.6,5.0),(15.8,2.0),
        (18.2,.6),(18.5,-.25),(18.2,-.64),(17.55,-.42),(15.6,1.28),(8.4,4.3),(1.65,5.54)],
        0,tau,48,'Iron')
    save('SmokeHood')


sack()
shade()
sleeper()
hood()
