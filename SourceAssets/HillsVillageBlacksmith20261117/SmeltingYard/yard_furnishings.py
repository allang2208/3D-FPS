"""Paired fuel bins, split billets and a parked two-wheel smith's handcart, in village-facing metres."""
import math
import random

def dress(box, beam, poly, solid):
    rng=random.Random(231123)

    def transform(x,y,angle):
        a=math.radians(angle)
        def point(u,v,z):
            return (x+u*math.cos(a)-v*math.sin(a),y+u*math.sin(a)+v*math.cos(a),z)
        return point

    def billet(x,y,z,length,radius,yaw,roll=0.):
        point=transform(x,y,yaw)
        # A sector cut out of the trunk. The two split planes, outer bark and transverse
        # end grain each use their own faces and UVs. The ends have individual tool marks.
        spread=rng.uniform(1.74,2.45)
        theta=[-spread/2+spread*k/7 for k in range(8)]
        section=[(0.,0.)]+[(radius*math.sin(t),radius*math.cos(t)*rng.uniform(.92,1.04)) for t in theta]
        angle=math.radians(roll)
        rotated=[(v*math.cos(angle)-h*math.sin(angle),v*math.sin(angle)+h*math.cos(angle)) for v,h in section]
        foot=min(p[1] for p in rotated)
        verts=[]
        for end in (-1,1):
            for v,h in rotated:
                verts.append(point(end*length/2+rng.uniform(-.013,.013),v,z+h-foot))
        n=len(rotated)
        faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
        indices=[0,0]
        end_uv=[(.5+.44*v/radius,.5+.44*h/radius) for v,h in section]
        uvs=[list(reversed(end_uv)),end_uv]
        for i in range(n):
            j=(i+1)%n
            faces.append((i,j,j+n,i+n))
            indices.append(1 if i in (0,n-1) else 2)
            offset=.17*(i if i else 1)
            uvs.append([(offset,.16),(offset+.11,.16),(offset+.11,.16+length),(offset,.16+length)])
        # The transverse ring above runs clockwise as seen from +X.
        for k in range(len(faces)):
            faces[k]=tuple(reversed(faces[k]))
            uvs[k]=list(reversed(uvs[k]))
        poly("Hand split firewood",verts,faces,["End","Split","Bark"],indices,uvs)

    def crate(x,y,angle,layers):
        p=transform(x,y,angle)
        length,width=1.06,.79
        for v in (-.29,.29):
            box("Bin runner",p(0,v,.045),(.99,.095,.09),"Oak",angle)
        for j in range(5):
            box("Bin flooring",p(0,(j-2)*.15,.112),(length,.145,.05),"Oak",angle)
        for u in (-.47,.47):
            for v in (-.33,.33):
                box("Bin corner cleat",p(u,v,.385),(.075,.075,.53),"Oak",angle)
        for j in range(3):
            z=.21+.166*j
            for side in (-1,1):
                box("Crate side slat",p(0,side*.372,z),(length,.042,.144),"Oak",angle)
                box("Crate end slat",p(side*.509,0,z),(.043,width-.055,.145),"Oak",angle)
        for side in (-1,1):
            for u in (-.447,.447):
                box("Bin hoop corner",p(u,side*.399,.375),(.037,.012,.47),"Iron",angle,.003)
        for layer in range(layers):
            # Gaps in the top row reveal the interior. The full bin shows bark over its rim.
            count=3 if layer==layers-1 and layers==2 else 4
            for row in range(count):
                for col in (-1,1):
                    px,py,pz=p(col*.236+rng.uniform(-.014,.014),(row-1.5)*.155+rng.uniform(-.013,.013),.14+layer*.104)
                    billet(px,py,pz,rng.uniform(.39,.45),rng.uniform(.096,.118),angle+rng.uniform(-4,4),rng.uniform(55,135))
        solid(p(0,0,.31),(length,width,.62),angle)

    crate(-.08,-2.82,-8,5)
    crate(1.26,-2.91,9,2)
    billet(.43,-2.19,.012,.39,.095,22,93)
    for _ in range(12):
        x,y=rng.uniform(-.48,1.92),rng.uniform(-2.39,-2.12)
        beam("Split kindling",(x,y,.013),(x+rng.uniform(.07,.22),y+rng.uniform(-.07,.07),.021),
             rng.uniform(.008,.019),.014,"Split")

    # Park alongside the crates, handles facing the loading side of the shop.
    cx,cy,yaw=4.75,-2.58,10.
    p=transform(cx,cy,yaw)
    def board(name,u,v,z,size,mat="Oak"):
        return box(name,p(u,v,z),size,mat,yaw)
    def rail(name,a,b,w,h,mat="Oak"):
        return beam(name,p(*a),p(*b),w,h,mat)
    def rim(v,r0,r1,width,mat):
        verts,faces=[],[]
        steps=40
        for k in range(steps):
            a=k*math.tau/steps
            for radius,side in [(r0,-1),(r1,-1),(r1,1),(r0,1)]:
                verts.append(p(-.18+radius*math.cos(a),v+side*width*.5,.472+radius*math.sin(a)))
        for k in range(steps):
            for j in range(4):
                i=k*4
                n=(k+1)%steps*4
                faces.append((i+j,i+(j+1)%4,n+(j+1)%4,n+j))
        poly("Cart wheel "+mat,verts,faces,[mat],[0]*len(faces))
    rail("Axle",(-.18,-.665,.472),(-.18,.665,.472),.09,.09,"Iron")
    for side in (-1,1):
        v=side*.571
        rim(v,.385,.451,.077,"Oak")
        rim(v,.448,.47,.084,"Iron")
        for i in range(10):
            a=.1+i*math.tau/10
            rail("Tapered oak spoke",(-.18+.067*math.cos(a),v,.472+.067*math.sin(a)),
                 (-.18+.402*math.cos(a),v,.472+.402*math.sin(a)),.044,.048)
        rail("Oak wheel hub",(-.18,v-.082,.472),(-.18,v+.082,.472),.129,.128)
        board("Axle pin",-.18,v+side*.09,.472,(.067,.035,.069),"Iron")
        rail("Underframe and shaft",(-.86,side*.36,.543),(1.96,side*.36,.81),.079,.094)
        rail("Cart grip",(1.73,side*.36,.79),(2.09,side*.36,.827),.06,.071)
        for u in (-.83,.57):
            rail("Side stanchion",(u,side*.416,.675),(u,side*.473,1.06),.049,.05)
        for z,vv in [(.776,.428),(.929,.452)]:
            if side==1 and z>.9:
                # An old impact has taken a splinter from the exposed edge of this board.
                line=[(-.90,-.061),(.62,-.061),(.62,.061),(.23,.061),(.13,.021),
                      (.09,.045),(.045,.010),(-.04,.043),(-.18,.061),(-.90,.061)]
                verts=[p(u,side*vv+d,z+h) for d in (-.023,.023) for u,h in line]
                n=len(line)
                faces=[tuple(range(n)),tuple(range(2*n-1,n-1,-1))]
                faces.extend((i,i+n,(i+1)%n+n,(i+1)%n) for i in range(n))
                poly("Splintered cart side",verts,faces,["Oak"],[0]*len(faces))
            else:
                board("Shallow bed plank",-.14,side*vv,z,(1.52,.046,.123))
        rail("Forged repair strap",(-.72,side*.477,.726),(-.42,side*.484,1.003),.046,.016,"Iron")
        for u,z in [(-.69,.756),(-.47,.962),(.50,.937)]:
            board("Hammered rivet",u,side*.490,z,(.026,.015,.024),"Iron")
        rail("Shaft ferrule",(1.67,side*.36,.782),(1.735,side*.36,.790),.085,.099,"Iron")
    for j in range(6):
        board("Cart bed deck",-.14,(j-2.5)*.146,.671,(1.47,.14,.07))
    for z in (.779,.931):
        board("Cart tailgate",-.887,0,z,(.047,.90,.126))
    rail("Parking prop",(.66,.08,.60),(.73,.08,.035),.08,.105)
    board("Wheel chock",-.55,-.573,.069,(.20,.138,.134))
    solid(p(-.14,0,.68),(1.53,.92,.69),yaw)
    for side in (-1,1):
        solid(p(-.18,side*.571,.46),(.78,.12,.87),yaw)
        solid(p(1.31,side*.36,.748),(1.54,.082,.12),yaw)
    for j in range(3):
        xx,yy,zz=p(-.38+.29*j,-.11+j*.085,.71)
        billet(xx,yy,zz,.47,.09,yaw+rng.uniform(5,24),rng.uniform(50,120))
