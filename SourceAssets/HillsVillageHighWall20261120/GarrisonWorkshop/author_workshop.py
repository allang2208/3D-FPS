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

# Exact Watchtower (SM_HighWatchtower at WorkshopTowerPose) bounds in Workshop local cm.
TOWER_X = -163.0
TOWER_QUOIN_X = -159.0
TOWER_Y_N = -399.74
TOWER_Y_S = 520.26
TOWER_N_QUOIN_Y = -403.74
TOWER_S_QUOIN_Y = 524.26
TOWER_N_FOOT_Y = -413.74
TOWER_S_FOOT_Y = 534.26
TOWER_NW_QUOIN_Y1 = -333.5
TOWER_SW_QUOIN_Y0 = 445.0
PORTAL_CY = 60.26
PORTAL_SILL = 345.0
PORTAL_SPRING = 530.0
PORTAL_R = 94.0

def splayed_y(z, is_north):
    """Linear splayed Watchtower footing face on North (-Y) or South (+Y) in Workshop coords."""
    t = max(0.0, min(1.0, (z - 9.0) / 80.0))
    return (-413.74 + 13.0 * t) if is_north else (534.26 - 13.0 * t)

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

def tower_portal_bulkhead(m):
    """Arched oak-and-iron shutter bulkhead sealing the Watchtower's 2F west wall-walk portal."""
    outer_span_r = 97.5
    plank_count = 12
    span = outer_span_r * 2.0
    bw = span / plank_count
    # Vertical oak boards fill the full 97.5 cm outer reveal (xw in [-162.8, -158.2]), clearing -158.0 voussoirs.
    for i in range(plank_count):
        yc = PORTAL_CY - outer_span_r + (i + 0.5) * bw
        dy = min(0.995, abs(yc - PORTAL_CY) / outer_span_r)
        arch_top = PORTAL_SPRING + 64.0 * math.sqrt(max(0.0, 1.0 - dy * dy)) - 0.3
        m.member((-160.5, yc, PORTAL_SILL), (-160.5, yc, arch_top), 4.5, bw - 0.15, "Oak")
    # Curved oak arched frame collar seals the arch shoulder corners with zero light leaks.
    seg_n = 16
    for i in range(seg_n):
        t0 = math.pi * i / seg_n
        t1 = math.pi * (i + 1) / seg_n
        r_in, r_out, r_arch_out = 86.0, 98.2, 64.0
        r_in_v = 54.0
        p0 = (-162.8, PORTAL_CY + r_in * math.cos(t0), PORTAL_SPRING + r_in_v * math.sin(t0))
        p1 = (-162.8, PORTAL_CY + r_in * math.cos(t1), PORTAL_SPRING + r_in_v * math.sin(t1))
        p2 = (-162.8, PORTAL_CY + r_out * math.cos(t1), PORTAL_SPRING + (r_arch_out + 2.0) * math.sin(t1))
        p3 = (-162.8, PORTAL_CY + r_out * math.cos(t0), PORTAL_SPRING + (r_arch_out + 2.0) * math.sin(t0))
        q0 = (-158.3, p0[1], p0[2])
        q1 = (-158.3, p1[1], p1[2])
        q2 = (-158.3, p2[1], p2[2])
        q3 = (-158.3, p3[1], p3[2])
        m.solid([[p0, p1, p2, p3], [q0, q1, q2, q3]], "Oak")
    # Vertical side stiles seal the octagonal board chamfer along the stone reveal jambs.
    for side_y in (PORTAL_CY - 96.2, PORTAL_CY + 96.2):
        m.member((-160.5, side_y, PORTAL_SILL), (-160.5, side_y, PORTAL_SPRING + 6.0), 4.5, 5.0, "Oak")
    # Recessed interior sill molding, center mullion, and forged horizontal hinge straps.
    m.member((-157.5, PORTAL_CY - 96.0, PORTAL_SILL + 4.0), (-157.5, PORTAL_CY + 96.0, PORTAL_SILL + 4.0), 5.0, 8.0, "Oak")
    m.member((-157.5, PORTAL_CY, 428.0), (-157.5, PORTAL_CY, 591.0), 3.2, 6.5, "Oak")
    m.member((-157.2, PORTAL_CY - 92.0, 429.0), (-157.2, PORTAL_CY + 92.0, 429.0), 4.2, 6.0, "Oak")
    for z in (452.0, 518.0):
        m.member((-157.4, PORTAL_CY - 88.0, z), (-157.4, PORTAL_CY + 88.0, z), 2.8, 5.6, "Iron")
        for y in (PORTAL_CY - 72.0, PORTAL_CY - 36.0, PORTAL_CY + 36.0, PORTAL_CY + 72.0):
            pin(m, (-156.2, y, z), (1.4, 0.0, 0.0), 1.6, "Iron")
    m.collision(-162.8, -156.5, PORTAL_CY - outer_span_r, PORTAL_CY + outer_span_r, PORTAL_SILL, PORTAL_SPRING + 64.0)

def tower_roof_flashing(m):
    """Stepped wrought-iron flashing and timber abutment beams sealing all Workshop-to-Tower roof seams."""
    # Continuous west-face apron flashing along xw = -158.8 (above slate edge) rising up Tower face.
    z_edge = roof_z(158.8)
    for seg_y0, seg_y1, x_back in (
        (-404.0, TOWER_NW_QUOIN_Y1, -158.8),
        (TOWER_NW_QUOIN_Y1, TOWER_SW_QUOIN_Y0, -162.5),
        (TOWER_SW_QUOIN_Y0, 524.5, -158.8),
    ):
        # Sloped apron riding on slate (z_edge + 4.2 to roof_z(142) + 4.2) + vertical upstand against stone.
        m.span(-158.8, -142.0, seg_y0, seg_y1, z_edge + 3.8, roof_z(142.0) + 3.8,
               z_edge + 6.4, roof_z(142.0) + 5.8, "Iron")
        m.block(x_back, -155.8, seg_y0, seg_y1, z_edge + 3.8, z_edge + 24.0, "Iron", False)
    for y in range(-360, 500, 90):
        x_pin = -155.8
        pin(m, (x_pin, float(y), z_edge + 16.0), (1.8, 0.0, 0.0), 1.7, "Iron")

    # Sloped North (-404.0) & South (+524.5) rake flashing & underside abutment beams for side-wing roofs.
    for is_north, y_cut, y_beam, y_lap, y_wall_far, y_wall_near in (
        (True, -404.0, -410.5, -418.0, -400.0, -403.9),
        (False, 524.5, 531.0, 538.5, 520.5, 524.4),
    ):
        m.member((-335.0, y_beam, roof_z(335.0) - 11.0), (-155.0, y_beam, roof_z(155.0) - 11.0), 11.0, 14.0, "Oak")
        # Outer section (x <= -238) reaches Tower stone wall (-400/+520.5); quoin section stops at quoin face (-403.9/+524.4).
        for x0, x1, y_up in ((-337.0, -238.0, y_wall_far), (-238.0, -158.8, y_wall_near)):
            za, zb = roof_z(abs(x0)), roof_z(abs(x1))
            ya, yb = sorted((y_lap, y_cut))
            m.span(x0, x1, ya, yb, za + 3.8, zb + 3.8, za + 6.2, zb + 6.2, "Iron")
            ua, ub = sorted((y_cut, y_up))
            m.span(x0, x1, ua, ub, za + 3.8, zb + 3.8, za + 23.0, zb + 23.0, "Iron")
            # Lead cap fillet covering seam corner.
            ca, cb = sorted((y_cut - (1.8 if is_north else -1.8), y_cut + (1.8 if is_north else -1.8)))
            m.span(x0, x1, ca, cb, za + 5.5, zb + 5.5, za + 23.0, zb + 23.0, "Iron")

def architecture(m):
    # Foundation and sub-paving follow the L-shaped perimeter around the Watchtower footprint.
    for x0, x1, y0, y1, has_floor_col in (
        (-158.8, 302.0, -585.0, 585.0, True),
        (-302.0, -158.8, -585.0, -414.0, True),
        (-302.0, -158.8, 534.5, 585.0, False),
    ):
        m.block(x0, x1, y0, y1, -115, -8, "Footing")
        m.block(min(x0, -300.0) if x0 < -160 else x0, min(x1, 300.0), max(y0, -583.0), min(y1, 583.0), -8, -3, "Paving")
        if has_floor_col:
            m.collision(max(x0, -300.0), min(x1, 300.0), y0, y1, -8, 0)
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
                if side == -1 and i >= 2:
                    if a >= -414.2:
                        continue
                    b = min(b, -414.2)
                    if b - a < 1.0:
                        continue
                m.member((x,a+.3,-1.9),(x,b-.3,-1.9),20.25,3.8,"Floorboard")
    # Floor-to-Tower transition stone margins and chamfered Oak floor skirting.
    m.block(-161.8, -156.8, -333.4, 444.9, -4.0, 0.0, "Paving", False)
    m.block(-158.8, -156.8, -414.0, -333.4, -4.0, 0.0, "Paving", False)
    m.block(-158.8, -156.8, 444.9, 524.5, -4.0, 0.0, "Paving", False)
    m.member((-158.8, -333.0, 6.0), (-158.8, 444.5, 6.0), 6.2, 12.0, "Oak")
    m.member((-276.0, -416.8, 5.5), (-158.8, -416.8, 5.5), 5.2, 11.0, "Oak")

    # West side (+X) retains its full wall and 3 timber casements.
    x = 290; lo, hi = 276, 302
    m.block(lo, hi, -585, 585, 0, 87, "ChapelWall")
    for cy in (-385, 0, 385):
        m.block(lo+5, hi-5, cy-102, cy+102, 87, 126, "Plaster")
        m.block(lo+5, hi-5, cy-102, cy+102, 253, 316, "Plaster")
        casement(m, 1, cy)
    for a, b in ((-585,-487), (-283,-102), (102,283), (487,585)):
        m.block(lo+5, hi-5, a, b, 87, 316, "Plaster")
    for z in (88, 310):
        m.member((x, -591, z), (x, 591, z), 31, 14)

    # East side (-X) returns cleanly into the Watchtower's North and South faces without windows or intrusion.
    for is_north, y0, y1, foot_y, wall_y, z_post_y in (
        (True, -585.0, -400.0, -414.0, -402.5, -408.0),
        (False, 520.5, 585.0, 534.5, 523.0, 528.0),
    ):
        fy0, fy1 = sorted((y0 if is_north else y1, foot_y))
        m.block(-302, -276, fy0, fy1, 0, 89.2, "ChapelWall")
        # Sloped masonry wedge grafts the side stone base onto the Watchtower's splayed footing.
        wedge_rings = []
        for zw in (9.0, 24.0, 89.2):
            yw_s = splayed_y(zw, is_north) - (0.3 if is_north else -0.3)
            wy0, wy1 = (foot_y, yw_s) if is_north else (yw_s, foot_y)
            wedge_rings.append([(-302.0, wy0, zw), (-276.0, wy0, zw), (-276.0, wy1, zw), (-302.0, wy1, zw)])
        m.solid(wedge_rings, "ChapelWall")
        m.block(-297, -281, y0, y1, 89.2, 316, "Plaster")
        m.member((-290, -591.0 if is_north else 591.0, 88), (-290, wall_y, 88), 31, 14)
        m.member((-290, -591.0 if is_north else 591.0, 310), (-290, -400.2 if is_north else 520.8, 310), 31, 14)
        m.member((-287, z_post_y, 89.2), (-287, z_post_y, 321.0), 23, 15)
    # Front-East bay diagonal brace proud of both plaster faces (-297..-281).
    m.member((-289, -562, 98), (-289, -416, 302), 22, 12)
    # Rear-East interior closure cheek wall seals the 27 cm crevice behind the Tower's SW corner.
    m.block(-158.8, -147.0, 521.5, 565.0, 0, 87, "ChapelWall")
    m.block(-158.0, -148.5, 521.5, 565.0, 87, 316, "Plaster")
    for z in (88, 310):
        m.member((-152.5, 521.5, z), (-152.5, 565.0, z), 12.0, 14)
    m.member((-152.5, 561.0, 0), (-152.5, 561.0, 321), 12.0, 14)

    for y in (-573,573):
        front=y<0
        stone_intervals=((-276,-118),(118,276)) if front else ((-276,276),)
        plaster_intervals=((-300,-118),(118,300)) if front else ((-300,300),)
        py0,py1=(y-10,y+8) if front else (y-8,y+10)
        for a,b in stone_intervals:
            m.block(a,b,y-12,y+12,0,87,"ChapelWall")
        for a,b in plaster_intervals:
            m.block(a,b,py0,py1,87,315,"Plaster")
        if front:m.block(-118,118,py0,py1,267,315,"Plaster")
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
            m.member((x,y,0),(x,y,302),22,22)
        for side in (-1,1):
            a,b=(side*129,side*272)
            m.member((a,y+(13 if not front else -13),101),(b,y+(13 if not front else -13),296),10,13)
    for y in (-570,-192,192,570):
        # West (+X) side post, knee brace, and principal rafter always run full span.
        m.member((287,y,0),(287,y,321),23,23)
        m.member((287,y,229),(210,y,309),14,15)
        m.member((318,y,roof_z(318)-11),(0,y,480),15,19)
        pin(m,(287,y-12,292),(0,-2,0),3.1,"Oak")
        if abs(y) == 570:
            m.member((-287,y,0),(-287,y,321),23,23)
            m.member((-287,y,229),(-210,y,309),14,15)
            m.member((-318,y,roof_z(318)-11),(0,y,480),15,19)
            pin(m,(-287,y-12,292),(0,-2,0),3.1,"Oak")
            m.member((-289,y,304),(289,y,304),17,22)
        else:
            # Engaged oak wall-pilaster, stone plinth, iron straps, shortened tie-beam, knee brace, and rafter.
            m.coping(-161.8, -142.0, y-13.5, y+13.5, 0.0, 22.0, "Coping")
            m.collision(-161.8, -142.0, y-13.0, y+13.0, 0.0, 22.0)
            m.member((-154.0, y, 20.0), (-154.0, y, 391.0), 16.5, 22.0)
            for z in (115.0, 220.0, 295.0):
                for dy in (-12.5, 12.5):
                    m.member((-162.5, y+dy, z), (-145.0, y+dy, z), 3.0, 6.0, "Iron")
                    pin(m, (-154.0, y+math.copysign(14.0, dy), z), (0.0, math.copysign(1.5, dy), 0.0), 1.7, "Iron")
            m.member((-161.5, y, 304.0), (289.0, y, 304.0), 17, 22)
            m.member((-152.0, y, 229.0), (-82.0, y, 304.0), 14, 15)
            m.member((-158.0, y, roof_z(158.0)-11.0), (0.0, y, 480.0), 15, 19)
            pin(m, (-146.0, y-12, 292), (0, -2, 0), 3.1, "Oak")
        m.member((0,y,315),(0,y,478),16,16)

    # Engaged Tower-wall corner pilasters, continuous wall-plate & roof ledgers, and Front-East alcove ledgers.
    m.member((-151.4, -408.0, 0.0), (-151.4, -408.0, 391.0), 14.8, 15.0)
    m.member((-151.4, 524.0, 0.0), (-151.4, 524.0, 391.0), 14.8, 15.0)
    m.member((-152.0, -408.0, 304.0), (-152.0, 524.0, 304.0), 13.5, 16.0)
    m.member((-152.0, -408.0, 388.0), (-152.0, 524.0, 388.0), 13.5, 15.0)
    m.block(-162.5, -158.5, -333.4, 444.9, 380.5, 395.5, "Oak", False)
    for y_cor in (-300.0, -70.0, 60.0, 320.0, 420.0):
        for z_cor in (294.5, 379.0):
            if z_cor > 350.0 and abs(y_cor - 60.0) < 10.0:
                continue
            m.member((-162.2, y_cor, z_cor), (-146.5, y_cor, z_cor), 4.8, 4.5, "Iron")
            m.member((-160.2, y_cor, z_cor - 11.0), (-160.2, y_cor, z_cor + 1.0), 4.5, 4.8, "Iron")
    for z_ledge in (92.0, 304.0):
        m.member((-287.0, -410.5, z_ledge), (-151.0, -410.5, z_ledge), 12.0, 14.0 if z_ledge < 100 else 16.0)

    # West (+X) roof boarding, slate courses, and eave fascia remain full length.
    m.incline(0, 337, -619, 619, roof_z(0), roof_z(337), 9, "Floorboard")
    # East (-X) roof boarding clips at xw = -159.0 along the Tower span while keeping front and rear wings.
    m.incline(-159.0, 0.0, -619.0, 619.0, roof_z(159.0), roof_z(0.0), 9.0, "Floorboard")
    m.incline(-337.0, -159.0, -619.0, -404.0, roof_z(337.0), roof_z(159.0), 9.0, "Floorboard")
    m.incline(-337.0, -159.0, 524.5, 619.0, roof_z(337.0), roof_z(159.0), 9.0, "Floorboard")

    for side in (-1,1):
        for row in range(9):
            x0=row*37.5; x1=min(339,x0+40.5)
            cuts=[-619]
            y=-619+(16 if row%2 else 33)
            while y<609:
                cuts.append(y);y+=m.rng.uniform(30,39)
            cuts.append(619)
            if side == 1:
                for y0,y1 in zip(cuts,cuts[1:]):
                    a,b=x0,x1
                    lift=m.rng.uniform(0,.65)
                    m.span(a,b,y0+.18,y1-.18,roof_z(a)+1+lift,roof_z(b)+1+lift,
                           roof_z(a)+3+lift,roof_z(b)+3+lift+2,"Slate")
            else:
                for y0, y1 in zip(cuts, cuts[1:]):
                    lift = m.rng.uniform(0, .65)
                    # Split slate shingle segments cleanly at Tower North (-404.0) and South (+524.5) boundaries.
                    pts = [y0] + [bp for bp in (-404.0, 524.5) if y0 + 0.5 < bp < y1 - 0.5] + [y1]
                    for sy0, sy1 in zip(pts, pts[1:]):
                        ym = 0.5 * (sy0 + sy1)
                        in_tower_span = (-404.0 <= ym <= 524.5)
                        if in_tower_span:
                            if x0 >= 158.8:
                                continue
                            cx0, cx1 = x0, min(x1, 158.8)
                        else:
                            cx0, cx1 = x0, x1
                        a, b = sorted((-cx0, -cx1))
                        m.span(a, b, sy0 + .18, sy1 - .18, roof_z(a) + 1 + lift, roof_z(b) + 1 + lift,
                               roof_z(a) + 3 + lift + 2, roof_z(b) + 3 + lift, "Slate")
    m.member((336,-622,roof_z(336)-5),(336,622,roof_z(336)-5),10,15)
    m.member((-336,-622,roof_z(336)-5),(-336,-400.2,roof_z(336)-5),10,15)
    m.member((-336,520.5,roof_z(336)-5),(-336,622,roof_z(336)-5),10,15)
    for y in range(-620,620,50):
        m.member((0,y,492),(0,min(y+49.5,620),492),21,11,"Slate")
    tower_roof_flashing(m)
    tower_portal_bulkhead(m)
    # Interactive AColdSteelDoubleDoor leaves replace the formerly parked exterior leaves; keep lintel beam!
    m.member((-134,-581,265),(134,-581,265),29,25)
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

def braided_rope_sweep(m, points, radius_cm=2.0, twist_pitch_cm=0.0, lobe_amp=0.0, sample_step_cm=2.0, uv_scale_cm=22.0):
    """Smooth radial-normal hemp rope sweep matching VillageStable M_StableWeatheredRope UVs."""
    raw = [np.asarray(p, dtype=float) for p in points]
    if len(raw) < 2:
        return
    # Uniform arc-length resampling keeps curvature & UVs uniform.
    pts = [raw[0]]
    for a, b in zip(raw, raw[1:]):
        dist = float(np.linalg.norm(b - a))
        if dist < 1e-5:
            continue
        steps = max(1, int(math.ceil(dist / sample_step_cm)))
        for s in range(1, steps + 1):
            pts.append(a + (b - a) * (s / steps))
    n_pts = len(pts)
    if n_pts < 2:
        return

    arc_len = [0.0] * n_pts
    frames = []
    t0 = pts[1] - pts[0]
    t0 /= max(1e-8, float(np.linalg.norm(t0)))
    up_ref = np.array((0.0, 0.0, 1.0)) if abs(t0[2]) < 0.92 else np.array((1.0, 0.0, 0.0))
    s_vec = np.cross(up_ref, t0)
    s_vec /= max(1e-8, float(np.linalg.norm(s_vec)))
    u_vec = np.cross(t0, s_vec)
    frames.append((s_vec, u_vec))
    prev_t = t0

    for i in range(1, n_pts):
        arc_len[i] = arc_len[i - 1] + float(np.linalg.norm(pts[i] - pts[i - 1]))
        ti = (pts[i + 1] - pts[i - 1]) if i + 1 < n_pts else (pts[i] - pts[i - 1])
        ti_len = float(np.linalg.norm(ti))
        ti = (ti / ti_len) if ti_len > 1e-8 else prev_t
        axis = np.cross(prev_t, ti)
        ax_len = float(np.linalg.norm(axis))
        if ax_len > 1e-6:
            axis /= ax_len
            angle = math.atan2(ax_len, float(np.clip(np.dot(prev_t, ti), -1.0, 1.0)))
            ca, sa = math.cos(angle), math.sin(angle)
            s_vec = s_vec * ca + np.cross(axis, s_vec) * sa + axis * (np.dot(axis, s_vec) * (1.0 - ca))
            s_vec /= max(1e-8, float(np.linalg.norm(s_vec)))
            u_vec = np.cross(ti, s_vec)
        frames.append((s_vec, u_vec))
        prev_t = ti

    m_pts = 12
    sec = []
    perim = [0.0]
    for k in range(m_pts):
        ang = k * math.tau / m_pts
        lobe = 1.0 + lobe_amp * math.cos(3.0 * ang)
        sec.append((radius_cm * lobe * math.cos(ang), radius_cm * lobe * math.sin(ang)))
    for k in range(m_pts):
        x0, y0 = sec[k]
        x1, y1 = sec[(k + 1) % m_pts]
        perim.append(perim[-1] + math.hypot(x1 - x0, y1 - y0))

    twist_per_cm = (math.tau / twist_pitch_cm) if twist_pitch_cm > 1e-3 else 0.0
    rings = []
    ring_norms = []
    for i in range(n_pts):
        sv, uv = frames[i]
        ang = arc_len[i] * twist_per_cm
        ca, sa = math.cos(ang), math.sin(ang)
        rs = ca * sv + sa * uv
        ru = -sa * sv + ca * uv
        r_pts = []
        r_nrm = []
        for x, y in sec:
            offset = x * rs + y * ru
            r_pts.append(pts[i] + offset)
            n_len = max(1e-8, float(np.linalg.norm(offset)))
            r_nrm.append((offset / n_len).tolist())
        rings.append(r_pts)
        ring_norms.append(r_nrm)

    g_uv = m.groups["Rope"]["uv0"]
    g_n = m.groups["Rope"]["normals"]
    for i in range(n_pts - 1):
        u0 = arc_len[i] / uv_scale_cm
        u1 = arc_len[i + 1] / uv_scale_cm
        lo, hi = rings[i], rings[i + 1]
        nlo, nhi = ring_norms[i], ring_norms[i + 1]
        for k in range(m_pts):
            k2 = (k + 1) % m_pts
            v0 = perim[k] / uv_scale_cm
            v1 = perim[k + 1] / uv_scale_cm
            m.triangle(lo[k], lo[k2], hi[k2], "Rope")
            g_uv[-3:] = [[u0, v0], [u0, v1], [u1, v1]]
            g_n[-3:] = [nlo[k], nlo[k2], nhi[k2]]
            m.triangle(lo[k], hi[k2], hi[k], "Rope")
            g_uv[-3:] = [[u0, v0], [u1, v1], [u1, v0]]
            g_n[-3:] = [nlo[k], nhi[k2], nhi[k]]

    for ring_pts, reverse in ((rings[0], True), (rings[-1], False)):
        center = sum(ring_pts) / m_pts
        for k in range(m_pts):
            a, b = ring_pts[k], ring_pts[(k + 1) % m_pts]
            if reverse:
                m.triangle(center, b, a, "Rope")
            else:
                m.triangle(center, a, b, "Rope")
            g_uv[-3:] = [[0.5, 0.5], [0.6, 0.5], [0.5, 0.6]]

def rope_on_floor(m,x,y):
    # Continuous smooth braided hemp coil and trailing end resting cleanly on floor.
    points=[]
    for i in range(129):
        t=i/128
        angle=t*math.tau*3.5
        r=9+15*t
        points.append((x+r*math.cos(angle),y+.85*r*math.sin(angle),2.25))
    last=points[-1]
    points += [(last[0]+dx,last[1]+dy,2.25) for dx,dy in ((0,-8),(-2,-16),(-7,-24),(-15,-28),(-21,-32))]
    braided_rope_sweep(m, points, radius_cm=2.1, twist_pitch_cm=18.0, lobe_amp=0.09, sample_step_cm=1.6, uv_scale_cm=22.0)

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
    rope_on_floor(m,-105,-260)
    # Under-bench lower rack holds spare wheel spokes sorted by length.
    for y in (-46,86):m.member((-142,y,20),(-83,y,20),9,8)
    for i in range(5):
        x=-141+i*11
        m.member((x,-61+i*3,27),(x+1,119-i*5,27),7,6)
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
    table(m,-112,30,84,264,91)
    table(m,217,-104,79,169,87)
    # Fixed storage shelves and straps on their uprights.
    for y in (160,490):
        for x in (188,261):m.member((x,y,0),(x,y,188),10,10)
    for z in (20,97,177):
        for x in (200,224,248):m.member((x,149,z),(x,500,z),23.6,6)
    m.collision(183,266,148,501,0,179)
    # The rear rig is longitudinal. Its bare axle and trestles remain clear of the Tower wall.
    cx,cy=-96,394
    for station in (-115,115):
        y=cy+station
        for side in (-1,1):
            m.member((cx+side*41,y,0),(cx+side*12,y,78),13,14)
        m.member((cx-47,y,21),(cx+47,y,21),10,11)
        m.member((cx-26,y,77),(cx+26,y,77),19,13)
        m.collision(cx-48,cx+48,y-10,y+10,0,83)
    spindle(m,(cx,cy-150,101),(cx,cy+155,101),[(0,11),(.06,11),(.08,17),(.92,17),(.95,11),(1,11)],"Oak",18)
    spindle(m,(cx,cy-84,101),(cx,cy+72,101),[(0,38),(.045,38),(.06,29),(.94,29),(.96,38),(1,38)],"Oak",24)
    # Continuous tightly-wound smooth helical hemp rope around winch barrel (y in [cy-67, cy+45], 24-sided concentric).
    winch_pts = []
    turns = 20.0
    steps_per_turn = 24
    total_steps = int(turns * steps_per_turn)
    y0_wrap, y1_wrap = cy - 66.5, cy + 44.5
    r_wrap = 31.1
    for i in range(-3, total_steps + 4):
        t_raw = i / total_steps
        t_clamped = max(0.0, min(1.0, t_raw))
        ang = t_raw * math.tau * turns
        wy = y0_wrap + (y1_wrap - y0_wrap) * t_clamped
        # Smoothly tuck start/end coils into the 29 cm oak drum core.
        tuck = max(0.0, (-i / 3.0) if i < 0 else ((i - total_steps) / 3.0 if i > total_steps else 0.0))
        r_cur = r_wrap - 3.6 * (tuck * tuck)
        winch_pts.append((cx + r_cur * math.cos(ang), wy, 101.0 + r_cur * math.sin(ang)))
    braided_rope_sweep(m, winch_pts, radius_cm=2.75, twist_pitch_cm=0.0, lobe_amp=0.0, sample_step_cm=9.0, uv_scale_cm=22.0)
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
