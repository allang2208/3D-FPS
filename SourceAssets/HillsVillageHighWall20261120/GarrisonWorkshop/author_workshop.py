"""East-gate roadside workshop, UE cm. The loading door faces -Y; finished floor is Z=0."""
from pathlib import Path
import math
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "Tools/WorldGeneration/HighVillageDefense"))
import source_mesh
from chapel_gatehouse import Kit, spindle, pin
from wall_geometry import Mesh
from workshop_frontage import entrance_hoist, trade_sign

TILES = {"ChapelWall":200, "Footing":125, "Coping":100, "Paving":145, "Oak":125,
         "Floorboard":180, "Iron":80, "Slate":105, "Plaster":160, "Rope":38, "Bronze":65,
         "SignOak":80,"ForgedStrap":48,"WheelBrass":31,"HempCord":8}

class Shop(Kit):
    def __init__(self, seed):
        super().__init__(seed)
        self.groups = {mat:{k:[] for k in ('vertices','normals','uv0','uv1','triangles')} for mat in TILES}
        self.grain = None
        self.phase = (0.,0.)

    def triangle(self,a,b,c,material,offset=(0.,0.)):
        Mesh.triangle(self,a,b,c,material,offset)
        g=self.groups[material]
        normal=g['normals'][-1]
        axis=max(range(3),key=lambda i:abs(normal[i]))
        u,v=((1,2),(0,2),(0,1))[axis]
        for i,p in zip((-3,-2,-1),(a,b,c)):
            across,along=p[u],p[v]
            if self.grain is not None and material in ("Oak","Floorboard","SignOak"):
                across,along=np.dot(p,self.grain[0]),np.dot(p,self.grain[1])
                if abs(np.dot(normal,self.grain[0]))>.85: across=np.dot(p,self.grain[2])
            g["uv0"][i]=[across/TILES[material]+self.phase[0],-along/TILES[material]+self.phase[1]]

    def member(self,a,b,width,depth,mat="Oak"):
        # Eight-sided section and pegged joinery retain an arris highlight at first-person distance.
        a,b=np.array(a,dtype=float),np.array(b,dtype=float)
        along=(b-a)/np.linalg.norm(b-a)
        across=np.cross((0.,0.,1.) if abs(along[2])<.98 else (0.,1.,0.),along)
        across/=np.linalg.norm(across)
        up=np.cross(along,across)
        w,h=width*.5,depth*.5
        cut=min(w*.18,h*.18,1.25)
        profile=[(-w+cut,-h),(w-cut,-h),(w,-h+cut),(w,h-cut),(w-cut,h),(-w+cut,h),(-w,h-cut),(-w,-h+cut)]
        self.phase=(self.rng.random(),self.rng.random())
        self.grain=(across,along,up)
        self.solid([[p+x*across+z*up for x,z in profile] for p in (a,b)],mat)
        self.grain=None

def roof_z(x):
    return 491.-abs(x)*.55

def casement(m,side,cy):
    """Joinery fills a reserved wall opening. Each crosslight stops at its receiving stile."""
    x=side*290
    m.member((x,cy-102,131.5),(x,cy+102,131.5),33,11)
    m.member((x,cy-102,247),(x,cy+102,247),27,12)
    m.collision(x-15,x+15,cy-102,cy+102,126,137)
    m.collision(x-12,x+12,cy-102,cy+102,241,253)
    for end in (-1,1):
        y=cy+end*96
        m.member((x,y,137),(x,y,241),24,12)
        m.collision(x-11,x+11,y-6,y+6,137,241)
        for z in (144,234):
            pin(m,(x+side*12,y,z),(side*1.4,0,0),2.1,"Oak")
    m.member((x,cy,137),(x,cy,241),16,10)
    m.collision(x-8,x+8,cy-5,cy+5,137,241)
    for a,b in ((-90,-5),(5,90)):
        m.member((x,cy+a,216),(x,cy+b,216),10,6)
        m.collision(x-5,x+5,cy+a,cy+b,213,219)

def architecture(m):
    # Foundation is buried; the entrance rises in two shallow courses from the yard.
    m.block(-302,302,-585,585,-115,-8,"Footing")
    m.block(-300,300,-583,583,-8,-3,"Paving")
    m.block(-134,134,-693,-639,-75,-14,"Footing")
    m.block(-140,140,-639,-584,-66,-7,"Footing")
    for y0,y1,z in [(-693,-639,-14),(-639,-584,-7)]:
        for i in range(4):
            m.coping(-136+i*68,-68+i*68,y0,y1,z-4,z+1,"Paving")
    # Setts fan out to the road shoulder. The floor datum is 15 cm above its soil.
    for row,(a,b) in enumerate(((-835,-789),(-789,-742),(-742,-694))):
        half=146-row*5
        cuts=[-half,-59,20,half] if row%2==0 else [-half,-89,-8,70,half]
        for i,(left,right) in enumerate(zip(cuts,cuts[1:])):
            top=-13.5+row*.35+(i%2)*.28
            m.coping(left+.65,right-.65,a+.7,b-.7,top-7,top,"Paving")
        m.collision(-half,half,a,b,-21,-13.6+row*.35)
    # Stone loading strip between the timber benches.
    for row,y in enumerate(range(-585,585,65)):
        cuts=[-116,-58,18,116] if row%2 else [-116,-24,53,116]
        for a,b in zip(cuts,cuts[1:]):
            m.coping(a+.3,b-.3,y+.4,min(y+64.6,585),-6,0,"Paving")
    for side in (-1,1):
        for i in range(9):
            x=side*(116+(i+.5)*20.6)
            cuts=[-583,-305,0,307,583] if i%2 else [-583,-441,-115,166,450,583]
            for a,b in zip(cuts,cuts[1:]):
                m.member((x,a+.3,-1.9),(x,b-.3,-1.9),20.25,3.8,"Floorboard")
    m.collision(-300,300,-585,585,-8,0)
    # Side elevations: stone lower wall, pale infill, three timber windows in true openings.
    for s in (-1,1):
        x=s*290; lo,hi=sorted((s*276,s*302))
        m.block(lo,hi,-585,585,0,87,"ChapelWall")
        for cy in (-385,0,385):
            m.block(lo+5,hi-5,cy-102,cy+102,87,126,"Plaster")
            m.block(lo+5,hi-5,cy-102,cy+102,253,316,"Plaster")
            casement(m,s,cy)
        for a,b in ((-585,-487),(-283,-102),(102,283),(487,585)):
            m.block(lo+5,hi-5,a,b,87,316,"Plaster")
        for z in (88,310):
            m.member((x,-591,z),(x,591,z),31,14)
    for y in (-573,573):
        front=y<0
        intervals=((-300,-118),(118,300)) if front else ((-300,300),)
        for a,b in intervals:
            m.block(a,b,y-12,y+12,0,87,"ChapelWall")
            m.block(a,b,y-10,y+10,87,315,"Plaster")
        if front:m.block(-118,118,y-10,y+10,267,315,"Plaster")
        # Vertical boards follow the gable slope. The front has an open louvred vent.
        for i in range(30):
            x=-290+i*20
            top=roof_z(abs(x)+10)-7
            bottom=385 if front and abs(x)<40 else 313
            m.member((x,y,bottom),(x,y,top),19.8,11,"Floorboard")
        for x0,x1 in zip((-300,-240,-180,-120,-40,40,120,180,240),(-240,-180,-120,-40,40,120,180,240,300)):
            bottom=385 if front and x0==-40 else 315
            m.collision(x0,x1,y-5,y+5,bottom,roof_z(max(abs(x0),abs(x1)))-7)
        if front:
            for z in (328,343,358,373):m.member((-43,y,z),(43,y,z),14,5)
        m.member((-301,y,311),(301,y,311),22,18)
        for x in (-118,118) if front else (-155,155):
            m.member((x,y,0),(x,y,315),23,23)
        for side in (-1,1):
            a,b=(side*129,side*272)
            m.member((a,y+(13 if not front else -13),101),(b,y+(13 if not front else -13),296),10,13)
    for y in (-570,-192,192,570):
        for s in (-1,1):
            x=s*287
            m.member((x,y,0),(x,y,321),23,23)
            m.member((x,y,229),(s*210,y,309),14,15)
            m.member((s*318,y,roof_z(318)-11),(0,y,480),15,19)
            pin(m,(x,y-12,292),(0,-2,0),3.1,"Oak")
        m.member((-289,y,304),(289,y,304),17,22)
        m.member((0,y,315),(0,y,478),16,16)
    # Roof boarding supports a broken-bond layer of individually chamfered slate courses.
    for side in (-1,1):
        a,b=sorted((0,side*337))
        m.incline(a,b,-619,619,roof_z(a),roof_z(b),9,"Floorboard")
        for row in range(9):
            x0=row*37.5; x1=min(339,x0+40.5)
            cuts=[-619]
            y=-619+(16 if row%2 else 33)
            while y<609:
                cuts.append(y);y+=m.rng.uniform(30,39)
            cuts.append(619)
            for y0,y1 in zip(cuts,cuts[1:]):
                a,b=sorted((side*x0,side*x1))
                lift=m.rng.uniform(0,.65)
                m.span(a,b,y0+.18,y1-.18,roof_z(a)+1+lift,roof_z(b)+1+lift,
                       roof_z(a)+3+lift+(2 if side<0 else 0),roof_z(b)+3+lift+(2 if side>0 else 0),"Slate")
        m.member((side*336,-622,roof_z(336)-5),(side*336,622,roof_z(336)-5),10,15)
    for y in range(-620,620,50):
        m.member((0,y,492),(0,min(y+49.5,620),492),21,11,"Slate")
    # Wide double door leaves are parked against the exterior wall.
    m.member((-134,-581,265),(134,-581,265),29,25)
    for side in (-1,1):
        for j in range(6):
            x=side*(129+18*j)
            m.member((x,-593,4),(x,-593,250),17.8,6,"Floorboard")
        for z in (48,199):
            m.member((side*122,-598,z),(side*226,-598,z),4,8,"Iron")
            for x in (134,178,220):pin(m,(side*x,-600,z),(0,-1.5,0),1.7,"Iron")
        m.member((side*128,-598,58),(side*218,-598,188),5,9)
    entrance_hoist(m)
    trade_sign(m)

def table(m,x,y,w,l,top):
    for sx in (-1,1):
        for sy in (-1,1):
            px,py=x+sx*(w*.5-8),y+sy*(l*.5-9)
            m.member((px,py,0),(px,py,top-9),12,12)
        m.member((x+sx*(w*.5-8),y-l*.5+5,30),(x+sx*(w*.5-8),y+l*.5-5,30),7,10)
    for i in range(4):
        px=x+(i-1.5)*w/4
        m.member((px,y-l*.5,top-5),(px,y+l*.5,top-5),w/4-.35,10)
    m.collision(x-w*.5,x+w*.5,y-l*.5,y+l*.5,0,top)

def rope_on_floor(m,x,y):
    # One continuous spiral and a slack end, with a round section and smooth bends.
    points=[]
    for i in range(129):
        t=i/128
        angle=t*math.tau*3.5
        r=9+15*t
        points.append((x+r*math.cos(angle),y+.85*r*math.sin(angle),2.15))
    last=points[-1]
    points += [(last[0]+dx,last[1]+dy,2.15) for dx,dy in ((0,-8),(-2,-16),(-7,-24),(-15,-28),(-21,-32))]
    path=np.asarray(points)
    rings=[]
    for i,point in enumerate(path):
        tangent=path[min(i+1,len(path)-1)]-path[max(i-1,0)]
        tangent/=np.linalg.norm(tangent)
        across=np.array((-tangent[1],tangent[0],0.))
        rings.append([point+2.1*(math.cos(a)*across+np.array((0.,0.,math.sin(a))))
                      for a in (math.tau*j/8 for j in range(8))])
    m.solid(rings,"Rope")

def floor_parts(m):
    # Receiving bay: a wooden axle on two padded skids, strapped iron collars and squared end.
    for y in (-471,-352):
        m.member((151,y,5),(255,y,5),16,10)
        for x in (177,216):m.member((x,y-7,14),(x,y+7,14),10,8)
    spindle(m,(196,-501,21),(196,-322,21),
            [(0,7),(.06,7),(.09,11),(.27,11),(.32,14),(.69,14),(.73,11),(.94,11),(.97,7),(1,7)],"Oak",16)
    for y in (-465,-354):
        spindle(m,(196,y-4,21),(196,y+4,21),[(0,11.5),(.15,12.5),(.85,12.5),(1,11.5)],"Iron",16)
    m.collision(148,258,-504,-319,0,31)
    # Open parts tray between the repair bench and the shelves. Pins lie inside the tray rails.
    for x in (184,204,224):m.member((x,40,2.5),(x,117,2.5),19.4,5)
    for x in (174,234):m.member((x,37,8),(x,120,8),4,10)
    for y in (39,118):m.member((176,y,8),(232,y,8),4,10)
    for i in range(4):
        x,y=181+11*i,55+(i%2)*12
        spindle(m,(x,y,8.2),(x+3,y+30,8.2),[(0,3),(.80,3),(.84,4.5),(1,4.5)],"Iron",10)
    for i in range(3):
        x,y=184+17*i,101+4*(i%2)
        # Four concentric rings form a thick washer with a visible bore.
        rings=[[(x+r*math.cos(j*math.tau/16),y+r*math.sin(j*math.tau/16),z)
                for j in range(16)] for r,z in ((6.8,5),(6.8,7.2),(3.1,7.2),(3.1,5))]
        m.rim(rings,"Iron")
    m.collision(172,236,36,121,0,13)
    rope_on_floor(m,-200,-173)
    # Under-bench lower rack holds spare wheel spokes sorted by length.
    for y in (19,151):m.member((-242,y,20),(-183,y,20),9,8)
    for i in range(5):
        x=-241+i*11
        m.member((x,4+i*3,27),(x+1,184-i*5,27),7,6)
    # A short tool rail on the inside of the rear wall, above the wheel and clear of the windows.
    m.member((-123,551,188),(123,551,188),9,16)
    for i,x in enumerate((-93,-49,-4,46,88)):
        pin(m,(x,546.5,188),(0,-8,0),2.3,"Iron")
        if i%2==0:
            m.member((x,540,144),(x,540,189),4,4)
            m.member((x-9,540,145),(x+10,540,145),6,7,"Iron")
        else:
            m.member((x,540,157),(x,540,190),5,5)
            m.member((x,540,145),(x,540,157),3,4,"Iron")

def fitout(m):
    floor_parts(m)
    # Standing place faces the long workbench from the central loading strip.
    table(m,-212,95,88,264,91)
    table(m,217,-104,79,169,87)
    # Fixed storage shelves and straps on their uprights.
    for y in (160,490):
        for x in (188,261):m.member((x,y,0),(x,y,188),10,10)
    for z in (20,97,177):
        for x in (200,224,248):m.member((x,149,z),(x,500,z),23.6,6)
    m.collision(183,266,148,501,0,179)
    # The rear rig is longitudinal. Its bare axle and trestles remain west of the through aisle.
    cx,cy=-211,394
    for station in (-115,115):
        y=cy+station
        for side in (-1,1):
            m.member((cx+side*41,y,0),(cx+side*12,y,78),13,14)
        m.member((cx-47,y,21),(cx+47,y,21),10,11)
        m.member((cx-26,y,77),(cx+26,y,77),19,13)
        m.collision(cx-48,cx+48,y-10,y+10,0,83)
    spindle(m,(cx,cy-150,101),(cx,cy+155,101),[(0,11),(.06,11),(.08,17),(.92,17),(.95,11),(1,11)],"Oak",18)
    spindle(m,(cx,cy-84,101),(cx,cy+72,101),[(0,38),(.045,38),(.06,29),(.94,29),(.96,38),(1,38)],"Oak",24)
    for offset in range(-67,45,5):
        spindle(m,(cx,cy+offset,101),(cx,cy+offset+4.4,101),[(0,29),(.26,31),(.74,31),(1,29)],"Rope",22)
    for offset in (-114,115):
        spindle(m,(cx,cy+offset-4,101),(cx,cy+offset+4,101),[(0,18),(1,18)],"Iron",20)
    m.collision(cx-17,cx+17,cy-149,cy+154,84,118)
    m.collision(cx-38,cx+38,cy-84,cy+72,64,139)
    # A wheel under repair; open spoke spaces and an iron tyre are readable against the rear wall.
    cx,cy,cz=78,530,65
    for i in range(16):
        a,b=math.tau*i/16,math.tau*(i+1)/16
        p=(cx+62*math.cos(a),cy,cz+62*math.sin(a))
        q=(cx+62*math.cos(b),cy,cz+62*math.sin(b))
        m.member(p,q,10,9)
        p2=(cx+66*math.cos(a),cy,cz+66*math.sin(a))
        q2=(cx+66*math.cos(b),cy,cz+66*math.sin(b))
        m.member(p2,q2,11,2.5,"Iron")
        if i%2==0:m.member((cx,cy,cz),p,7,6)
    spindle(m,(cx,cy-12,cz),(cx,cy+12,cz),[(0,12),(.25,14),(.8,14),(1,12)],"Oak",14)

if __name__=="__main__":
    source_mesh.OUT=HERE
    shell=Shop(71361); architecture(shell); shell.save("SM_GarrisonWorkshop")
    if "--shell-only" not in sys.argv:
        fittings=Shop(71139); fitout(fittings); fittings.save("SM_GarrisonAssemblyBay")
