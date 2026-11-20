"""Stonework above the original square throat on tavern 02. Dimensions in cm."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'VillagePerimeter'))
from wall_geometry import Mesh


class StackMesh(Mesh):
    def __init__(self, seed):
        super().__init__(seed)
        for slot in ('Soot', 'Lead', 'HearthStone'):
            self.groups[slot] = {k: [] for k in self.groups['Mortar']}

    def quad(self, a, b, c, d, slot):
        self.triangle(a, b, c, slot)
        self.triangle(a, c, d, slot)

    def square(self, r, z):
        return [(-r,-r,z), (r,-r,z), (r,r,z), (-r,r,z)]

    def join(self, low, high, slot):
        for i, a in enumerate(low):
            j = (i+1) % len(low)
            self.quad(a, low[j], high[j], high[i], slot)

    def sleeve(self, profile):
        """Annular baffled masonry, including the dark faces seen down the bore."""
        for (z0, out0, in0), (z1, out1, in1) in zip(profile, profile[1:]):
            self.join(self.square(out0, z0), self.square(out1, z1), 'Mortar')
            self.join(self.square(in1, z1), self.square(in0, z0), 'Soot')
        z, outer, inner = profile[0]
        self.join(self.square(inner, z), self.square(outer, z), 'Soot')
        z, outer, inner = profile[-1]
        self.join(self.square(outer, z), self.square(inner, z), 'Soot')

    def course(self, index, low, high, outer, joints, damaged=False, coping=False):
        bore = 15.4
        rng = self.rng
        for side in range(4):
            # Headers cross the end of the next stretcher on alternate lifts.
            long = (side+index) % 2 == 0
            span = outer if long else bore
            n = joints if long else 1
            cuts = [-span]+[-span+2*span*i/n+rng.uniform(-1.5,1.5) for i in range(1,n)]+[span]
            for j, (start, end) in enumerate(zip(cuts, cuts[1:])):
                if damaged and side == 1:
                    continue
                top = high - (5.5 if damaged and side == 0 and j == 0 else 0.)
                if side in (0, 2):
                    x0,x1 = start+.08, end-.08
                    y0,y1 = (-outer,-bore) if side==0 else (bore,outer)
                else:
                    y0,y1 = start+.08,end-.08
                    x0,x1 = (bore,outer) if side==1 else (-outer,-bore)
                mat = 'YardCap' if coping else ('YardField' if rng.random() < .30 else 'HearthStone')
                self.stone(x0,x1,y0,y1,low+.12,top-.22,mat)


def head(ruined):
    # The original hearth has a through bore up to its old weathering course.
    # Its top ring (room Z 662.9) becomes the bearing course of this extension.
    mesh = StackMesh(4917)
    end = 41. if ruined else 90.
    profile = [(-.6,20.6,15.2),(6.,20.9,15.2)]
    if ruined:
        profile += [(26.6,20.8,15.2)]
    else:
        profile += [(56.,20.9,15.2),(60.,22.1,15.2),(71.,23.2,15.2),
                    (74.,25.1,15.2),(79.,25.1,15.2),(86.,22.9,15.2),
                    (89.5,21.7,15.2)]
    mesh.sleeve(profile)
    levels = [(0.,13.5,22.5),(13.5,27.0,22.5),(27.,41.,22.8)]
    if not ruined:
        levels += [(41.,56.,22.7),(56.,69.,24.),(69.,79.,27.1),(79.,end,24.)]
    for i,(bottom, top, outer) in enumerate(levels):
        mesh.course(i, bottom, top, outer, 2, damaged=ruined and i==2,
                    coping=not ruined and i>=5)
    return mesh


def flashing(seat):
    mesh = StackMesh(8311)

    def ribbon(ribs):
        # A dressed lead sheet has a folded outer hem and a short chased
        # return into the masonry. All profiles follow the local slate faces.
        for a,b in zip(ribs,ribs[1:]):
            for i in range(len(a)-1):
                mesh.quad(a[i], b[i], b[i+1], a[i+1], 'Lead')
                c,d,e,f=(tuple((p[0],p[1],p[2]-.42)) for p in (a[i],b[i],b[i+1],a[i+1]))
                mesh.quad(f,e,d,c,'Lead')
        rim=[row[0] for row in ribs]+ribs[-1][1:]+[r[-1] for r in reversed(ribs[:-1])]+list(reversed(ribs[0][1:-1]))
        for a,b in zip(rim,rim[1:]+rim[:1]):
            mesh.quad(a,(a[0],a[1],a[2]-.42),(b[0],b[1],b[2]-.42),b,'Lead')

    # Draw each side's individual soakers over the lap below. Their upper
    # edges meet the old 17.4 cm coursing; each sheet turns below the next slate.
    for side in (-1,1):
        for i, (down,up) in enumerate(((27,8),(13,-8),(-3,-25))):
            ribs=[]
            for t in (0.,.25,.50,.75,1.):
                y=round(down+(up-down)*t,2)
                inner=side*20.85
                at=seat(inner,y)
                outer=side*(35.+i*.8)
                turn=seat(outer,y)+.50
                middle=side*27.8
                bed=3.1+i*17.4
                # The front side starts on a lower brick course.
                top=max(at+7.5, bed)
                profiles=[(outer,y,turn-.72),(outer-side*.6,y,turn+.65),
                          (middle,y,seat(middle,y)+1.16),(inner,y,at+2.15),
                          (inner+side*.8,y,top-.92),(inner-side*1.65,y,top)]
                ribs.append(profiles)
            if side==1:ribs.reverse()
            ribbon(ribs)

    # One upper back gutter divides water around the flue; the lower apron
    # laps the side pieces and discharges onto the full slate below the cut.
    for side in (-1,1):
        ribs=[]
        for x in (-36.,-30.,-24.,-18.,-12.,-6.,0.,6.,12.,18.,24.,30.,36.):
            wing=max(0.,abs(x)-20.5)
            up = side<0
            width = max(0.,1.-abs(x)/36.)
            inner=side*(21.5+wing*.27)
            outer=side*((42. if up else 44.)-wing*.35)
            mid=inner+(outer-inner)*.58
            at=seat(x,inner)
            roll=seat(x,outer)+.62
            saddle = width*3.8 if up else .3
            xwall=max(-20.6,min(20.6,x))
            # At the four ears, taper the fold into the side weathering.
            rise=(14.5 if up else 12.) * max(.17,1.-wing/17.)
            profiles=[(x,outer,roll-.68),(x,outer-side*.68,roll+.70),
                      (x,mid,seat(x,mid)+1.2+saddle*.55),(x,inner,at+1.7+saddle),
                      (xwall+(x-xwall)*.94,inner+side*.7,at+rise),
                      (xwall+(x-xwall)*.94,inner-side*1.65,at+rise+.68)]
            ribs.append(profiles)
        if side>0:ribs.reverse()
        ribbon(ribs)
    return mesh
