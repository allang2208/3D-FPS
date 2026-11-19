"""Throw, trim and handle four inn vessels. The working drawings below use centimetres."""
from bisect import bisect_right
from math import atan2, cos, exp, hypot, pi, sin, tau
from pathlib import Path
import sys

import bpy


HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / "SourceAssets/HillsVillageTavern/StonewareDetail"
SERVICE = OUT.parent / "Service"
CLAY, HONEY, OLIVE, ASH = "Clay", "HoneyGlaze", "OliveGlaze", "AshGlaze"


class Skin:
    def __init__(self):
        self.points, self.faces, self.uvs, self.slots, self.smoothing = [], [], [], [], []

    def point(self, x, y, z):
        self.points.append((x, y, z))
        return len(self.points) - 1

    def face(self, indices, coords, slot, smooth=True):
        self.faces.append(indices)
        self.uvs.append(coords)
        self.slots.append(slot)
        self.smoothing.append(smooth)

    def mesh_object(self, name):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([tuple(v * .01 for v in p) for p in self.points], [], self.faces)
        mesh.update()
        names = list(dict.fromkeys(self.slots))
        for slot in names:
            mesh.materials.append(bpy.data.materials[slot])
        uv = mesh.uv_layers.new(name="KilnUV")
        for poly, slot, coords, smooth in zip(mesh.polygons, self.slots, self.uvs, self.smoothing):
            poly.material_index = names.index(slot)
            poly.use_smooth = smooth
            for loop, coord in zip(poly.loop_indices, coords):
                uv.data[loop].uv = coord
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        return obj


class Wall:
    """A section runs from the recessed underside up the wall and back to the inner floor."""
    def __init__(self, glaze, lod):
        self.glaze, self.lod, self.section = glaze, lod, []

    def course(self, r, z, slot=None, mark="", max_lod=2):
        if self.lod <= max_lod:
            self.section.append((r, z, slot or self.glaze, mark))

    def line(self, points, slot=None):
        for r, z in points:
            self.course(r, z, slot)


def pitcher_section(lod):
    p = Wall(HONEY, lod)
    p.line([(.36,.48),(2.65,.52),(4.18,.48),(4.40,.35),(4.48,.10),
            (4.66,0),(5.15,0),(5.31,.10),(5.43,.29),(5.42,.52)], CLAY)
    p.course(5.30,.64,CLAY,max_lod=1)
    p.line([(5.32,.87),(5.56,1.05),(5.65,1.25),(5.56,1.47),(5.66,1.8)],CLAY)
    p.course(5.99,2.52, HONEY, "dip")
    p.line([(6.62,3.92),(7.31,5.40),(8.02,7.15),(8.46,8.77),
            (8.64,9.46),(8.74,10.00),(8.79,10.56),(8.81,11.07),(8.82,11.55),
            (8.78,12.15),(8.73,12.66)])
    # Two wheel-tool cuts enclose a meandering hand-incised wheat-colour band.
    p.course(8.68,12.89)
    p.course(8.54,13.03,HONEY,max_lod=1)
    p.course(8.60,13.14)
    p.course(8.52,13.60,HONEY,"comb")
    p.course(8.40,13.67,CLAY,"comb")
    p.course(8.42,13.76,HONEY,"comb")
    p.course(8.44,13.81,HONEY,"comb",1)
    p.course(8.30,14.42)
    p.course(8.12,14.52,HONEY,max_lod=1)
    p.course(8.19,14.66)
    p.line([(7.95,15.28),(7.52,16.05),(7.03,16.68),(6.30,17.36),
            (5.50,18.06),(5.07,18.65),(4.86,19.24),(4.82,19.75),
            (4.79,20.18),(4.80,20.62),(4.84,21.10),(4.88,21.55),(4.95,22.02),
            (5.04,22.45),(5.25,23.05),(5.48,23.61),(5.68,23.85),(5.81,24.04),
            (5.79,24.28),(5.65,24.46),(5.43,24.54),(5.19,24.46),(5.03,24.28),
            (4.98,24.04),(4.81,23.44),(4.60,22.67),(4.38,21.69),(4.25,20.43),
            (4.28,19.55),(4.48,18.77),(4.94,18.09),(5.95,17.07),(6.91,15.97),
            (7.62,14.61),(8.09,12.85),(8.17,11.18),(8.05,9.20),(7.49,7.37),
            (6.60,5.35),(5.71,3.79),(4.88,2.46),(4.25,1.88),(3.51,1.62),
            (2.08,1.54),(.32,1.54)])
    return p.section


def mug_section(lod):
    p = Wall(OLIVE, lod)
    p.line([(.28,.35),(2.72,.36),(3.39,.31),(3.49,.12),(3.60,0),(4.09,0),
            (4.29,.12),(4.39,.34),(4.38,.58),(4.22,.78),(4.23,.98)], CLAY)
    p.course(4.35,1.17,OLIVE,"dip")
    p.line([(4.49,1.48),(4.71,1.88),(4.91,2.40),(5.06,2.86),(5.17,3.36),
            (5.24,3.83),(5.29,4.32),(5.30,4.70),(5.25,5.30),(5.16,5.84)])
    p.course(4.99,6.13)
    p.course(4.85,6.27,OLIVE,max_lod=1)
    p.course(4.95,6.35)
    p.course(5.02,6.47)
    p.course(4.99,6.61)
    p.line([(4.85,6.75),(4.69,7.24),(4.57,7.77),(4.55,8.21),(4.57,8.62),
            (4.62,9.00),(4.68,9.38),(4.76,9.74),(4.82,10.08),(4.90,10.20)])
    p.course(5.00,10.28)
    p.course(5.04,10.38,OLIVE,max_lod=1)
    p.line([(5.01,10.56),(4.89,10.71),(4.68,10.77),(4.48,10.72),(4.33,10.57),
            (4.28,10.33),(4.16,9.69),(4.05,8.98),(3.99,8.30),(4.01,7.74),
            (4.20,6.89),(4.53,5.76),(4.65,4.73),(4.61,3.81),(4.39,2.75),
            (4.05,1.92),(3.63,1.51),(3.10,1.36),(1.9,1.27),(.28,1.26)])
    return p.section


def deform(role, r, z, mark, a, exterior):
    # The support rings sit flat. Wheel eccentricity and the undulating glaze stop
    # start above them. The same throwing eccentricity applies inside and out.
    fade = min(1.,max(0.,(z-.19)/1.6))
    rr = r*(1 + fade*(.0085*sin(3*a + .075*z + .6) + .0041*sin(5*a-.09*z)))
    h = z
    if mark == "dip":
        run = max(exp(-19*(1-cos(a-1.04))),.70*exp(-27*(1-cos(a+1.47))))
        depth = .83 if role=="Pitcher" else .45
        h += depth*(.20*sin(3*a+.4)+.10*sin(5*a)-.78*run)
        rr += (h-z)*(.42 if role=="Pitcher" else .31)
    if role == "Pitcher":
        if exterior and 2.8 < z < 19.24:
            rr += .044*sin(z*3.65+.21*sin(a)+.14*sin(2*a)) + .019*cos(z*5.0)
        if mark == "comb":
            wave = .33*cos(8*a+.38*sin(2*a))+.07*cos(16*a+.6)
            h += wave
            rr -= .21*wave
        t = min(1.,max(0.,(z-21.6)/2.9))
        delta = a-pi+.045
        pulled = exp(-5.4*(1-cos(delta)))
        shoulders = exp(-28*(1-cos(delta+.60)))+exp(-28*(1-cos(delta-.60)))
        rr += t*t*(2.12*pulled-.66*shoulders)
        h += t*t*(.83*pulled-.26*shoulders+.09*sin(3*a))
        yscale = 1-t*t*.22*pulled
    else:
        yscale = 1.
        if exterior and 1.0 < z < 6.5:
            flute = max(0.,sin(pi*(z-1.0)/5.5))**.85
            rr += flute*(.14*cos(12*a+.15*z)-.038*cos(24*a+.30*z))
        if z>9.5:
            h += .085*min(1.,z-9.5)*(sin(3*a+.4)+.34*sin(5*a))
    return rr*cos(a), rr*sin(a)*yscale, h


def foot_finish(slot, course, angle):
    # Three small reduction marks sit inside the foot's shaved edge. The bare
    # clay landing ring between them remains level against the shelf or table.
    if slot == CLAY and 2 <= course <= 4:
        width=(.11,.21,.075)[course-2]
        for centre,spread in ((.40,1.),(2.62,.61),(4.94,.83)):
            if cos(angle-centre-.042*(course-3)) > cos(width*spread):
                return OLIVE
    return slot


def construct_vessel(skin, role, lod):
    big = role == "Pitcher"
    profile = pitcher_section(lod) if big else mug_section(lod)
    segments = (120,64,32)[lod]
    summit = next(i for i,p in enumerate(profile) if p[1] == (24.54 if big else 10.77))
    # The strip between each pair of heights is removed from the outside wall.
    # The ribbon is sewn to these very vertices, leaving both the hollow interior
    # and all handle roots closed, with no intersecting shells.
    holes = ((20.18,22.45,1.79),(9.46,12.15,1.91)) if big else (
            (7.77,9.74,1.28),(2.40,4.32,1.39))
    windows = []
    for low,high,wide in holes:
        j0,j1 = (next(i for i,p in enumerate(profile[:summit]) if p[1]==h) for h in (low,high))
        half = max(1,round(segments*wide/(tau*profile[(j0+j1)//2][0])))
        windows.append((j0,j1,half))
    courses = []
    distances = [0.]
    for j,(r,z,slot,mark) in enumerate(profile):
        if j:
            distances.append(distances[-1]+hypot(r-profile[j-1][0],z-profile[j-1][1]))
        row = []
        for i in range(segments):
            a = i*tau/segments
            angular_i = i if i < segments//2 else i-segments
            h = z
            for low,high,half in windows:
                if low <= j <= high and abs(angular_i) <= half:
                    # Rounded corners at a pressed/smeared finger join.
                    center_z=(profile[low][1]+profile[high][1])*.5
                    h -= (z-center_z)*.25*(abs(angular_i)/half)**3
                    a -= angular_i*tau/segments*.18*(abs(z-center_z)/(profile[high][1]-center_z))**3
            row.append(skin.point(*deform(role,r,h,mark,a,j<summit)))
        courses.append(row)
    for j in range(len(profile)-1):
        for i in range(segments):
            signed = i if i<segments//2 else i-segments
            if any(lo<=j<hi and -half<=signed<half for lo,hi,half in windows):
                continue
            k = (i+1)%segments
            vertices = (courses[j][i],courses[j][k],courses[j+1][k],courses[j+1][i])
            planar = j < 3 or j >= len(profile)-4
            uv = ([(skin.points[q][0]/28+.5,skin.points[q][1]/28+.5) for q in vertices] if planar else
                  [(i/segments,distances[j]/26),((i+1)/segments,distances[j]/26),
                   ((i+1)/segments,distances[j+1]/26),(i/segments,distances[j+1]/26)])
            skin.face(vertices,uv,foot_finish(profile[j][2],j,(i+.5)*tau/segments))
    for j in (0,-1):
        row = courses[j]
        centre = skin.point(0,0,profile[j][1])
        for i in range(segments):
            tri = [row[i],row[(i+1)%segments],centre]
            if j==0:
                tri.reverse()
            skin.face(tri,[(skin.points[q][0]/28+.5,skin.points[q][1]/28+.5) for q in tri],profile[j][2])
    rims=[]
    for end,(low,high,half) in enumerate(windows):
        start,finish = (low,high) if end==0 else (high,low)
        step = 1 if end==0 else -1
        lattice = ([(k,start) for k in range(0,half+1)]
                   + [(half,j) for j in range(start+step,finish+step,step)]
                   + [(k,finish) for k in range(half-1,-half-1,-1)]
                   + [(-half,j) for j in range(finish-step,start-step,-step)]
                   + [(k,start) for k in range(-half+1,0)])
        coords = []
        for i,j in lattice:
            angle = atan2(i/half,(2*(profile[j][1]-profile[finish][1])/
                          (profile[start][1]-profile[finish][1])-1)) % tau
            coords.append((angle/tau,courses[j][i%segments]))
        rims.append(coords)
    ribbon(skin, role, lod, rims)


def smooth_path(keys, per_span):
    for j in range(len(keys)-1):
        a,b,c,d = (keys[min(len(keys)-1,max(0,k))] for k in (j-1,j,j+1,j+2))
        for step in range(per_span):
            t=step/per_span
            yield tuple(.5*((2*v)+(-u+w)*t+(2*u-5*v+4*w-x)*t*t+
                         (-u+3*v-3*w+x)*t*t*t) for u,v,w,x in zip(a,b,c,d))
    yield keys[-1]


def stitch(skin, lower, upper, v0, v1, slot):
    """Bridge rings with different vertex counts without splitting the handle root."""
    i=j=0
    a,b = lower+[(1.,lower[0][1])],upper+[(1.,upper[0][1])]
    while i<len(lower) or j<len(upper):
        ai = a[i+1][0] if i<len(lower) else 2.
        bj = b[j+1][0] if j<len(upper) else 2.
        poly,uv = [a[i][1]],[(a[i][0],v0)]
        if ai <= bj+1e-7:
            i+=1
            poly.append(a[i][1])
            uv.append((a[i][0],v0))
        if bj <= ai+1e-7:
            poly.append(b[j+1][1])
            uv.append((b[j+1][0],v1))
        poly.append(b[j][1])
        uv.append((b[j][0],v1))
        if bj <= ai+1e-7:
            j+=1
        skin.face(poly,uv,slot)


def ribbon(skin, role, lod, rims):
    big = role=="Pitcher"
    # Each profile is x,z,half-width,half-thickness. The wide starting pad,
    # concave thumb trough and thickened lower smear are part of the strap.
    keys = ([(5.03,21.32,1.66,.96),(5.54,21.41,1.52,.80),(6.36,21.64,1.33,.67),
             (7.56,21.80,1.16,.65),(8.78,21.59,1.09,.67),(9.85,20.89,1.06,.71),
             (10.78,19.49,1.06,.75),(11.43,17.70,1.05,.75),(11.61,16.00,1.01,.72),
             (11.36,14.43,.98,.67),(10.80,12.98,1.04,.65),(10.11,11.77,1.17,.72),
             (9.42,11.11,1.43,.89),(8.98,10.88,1.64,1.09)] if big else
            [(4.85,8.76,1.18,.78),(5.23,8.94,1.11,.67),(5.79,9.22,.96,.61),
             (6.40,9.37,.88,.63),(7.12,9.30,.82,.62),(7.73,8.88,.80,.60),
             (8.04,8.05,.77,.61),(8.04,7.11,.76,.60),(7.82,6.15,.77,.58),
             (7.41,5.17,.79,.56),(6.86,4.35,.83,.56),(6.22,3.77,.92,.57),
             (5.71,3.44,1.05,.66),(5.31,3.36,1.23,.83)])
    path = list(smooth_path(keys,(3,2,1)[lod]))
    sides = (24,16,10)[lod]
    prev, previous_v = rims[0],0.
    for j,(x,z,w,h) in enumerate(path):
        a,b = path[max(j-1,0)],path[min(j+1,len(path)-1)]
        dx,dz = b[0]-a[0],b[1]-a[1]
        norm = hypot(dx,dz)
        progress = j/(len(path)-1)
        section=[]
        for k in range(sides):
            angle=k*tau/sides
            c,s = cos(angle),sin(angle)
            # An oval ribbon flattened on its back with two finger-drawn rails.
            outside=max(0.,-c)
            finger=exp(-(s/.37)**2)
            profile=h*c+.13*outside**2*finger-.065*outside*exp(-((abs(s)-.57)/.19)**2)
            shift=(.17 if big else .10)*sin(pi*progress)**2
            section.append((k/sides,skin.point(x+dz/norm*profile,w*s+shift,z-dx/norm*profile)))
        v=(.055+progress*.89)
        stitch(skin,prev,section,previous_v,v,HONEY if big else OLIVE)
        prev,previous_v=section,v
    stitch(skin,prev,rims[1],previous_v,1.,HONEY if big else OLIVE)


def dish_section(lod):
    p=Wall(ASH,lod)
    p.line([(.31,.52),(3.52,.52),(4.67,.49),(5.05,.39),(5.26,.20),(5.33,.06),
            (5.43,0),(5.76,0),(5.89,.08),(6.00,.23),(6.06,.48),(6.19,.60)],CLAY)
    p.course(6.72,.73,ASH,"dip")
    p.line([(7.65,.89),(8.85,1.13),(9.95,1.44),(10.85,1.76),(11.70,2.07),
            (12.48,2.46),(13.04,2.75),(13.31,2.88),(13.46,3.01),(13.51,3.16),
            (13.47,3.28),(13.36,3.38),(13.18,3.43),(12.94,3.43),
            (12.69,3.38),(12.43,3.31)])
    p.course(12.29,3.25,HONEY)
    p.course(12.18,3.19,ASH)
    p.course(12.04,3.15,ASH,"reed")
    p.course(11.88,3.085,HONEY,"reed")
    p.course(11.78,3.055,ASH,"reed")
    p.line([(11.56,3.00),(11.06,2.84),(10.41,2.57),(9.72,2.34),
            (8.88,2.12),(7.89,1.92),(6.53,1.78),(6.02,1.75),(5.22,1.75),
            (4.81,1.66),(4.10,1.48),(3.22,1.32),(1.79,1.25),(.31,1.25)])
    return p.section


def plate_point(r,z,a,mark=""):
    outer = max(0.,min(1.,(r-6.20)/7.0))
    if mark=="reed":
        stroke=.14*cos(15*a+.28*sin(3*a))
        r+=stroke
        z+=.30*stroke
    if mark=="dip":
        r+=.29*sin(4*a+.2)+.15*sin(7*a)
    radius=r*(1+outer*(.005*sin(3*a+.8)+.0036*sin(5*a)))
    return (radius*cos(a),radius*sin(a),z+outer*(.076*sin(3*a+.5)+.037*cos(5*a)))


def flat_uv(skin,ids):
    return [(skin.points[i][0]/28+.5,skin.points[i][1]/28+.5) for i in ids]


def dish(skin,lod):
    n=(120,64,32)[lod]
    profile=dish_section(lod)
    rings=[[skin.point(*plate_point(r,z,tau*k/n,mark)) for k in range(n)] for r,z,slot,mark in profile]
    rim=next(j for j,p in enumerate(profile) if p[0]==13.51)
    for j in range(len(rings)-1):
        for k in range(n):
            nxt=(k+1)%n
            ids=[rings[j][k],rings[j][nxt],rings[j+1][nxt],rings[j+1][k]]
            if rim-2<=j<=rim+2:
                uv=[(k/n,j*.026),((k+1)/n,j*.026),((k+1)/n,(j+1)*.026),(k/n,(j+1)*.026)]
            else:
                uv=flat_uv(skin,ids)
            skin.face(ids,uv,foot_finish(profile[j][2],j,(k+.5)*tau/n))
    for j in (0,-1):
        centre=skin.point(0,0,profile[j][1])
        for k in range(n):
            ids=[rings[j][k],rings[j][(k+1)%n],centre]
            if j==0:
                ids.reverse()
            skin.face(ids,flat_uv(skin,ids),profile[j][2])


def interp(points,x):
    i=max(0,min(len(points)-2,bisect_right([p[0] for p in points],x)-1))
    a,b=points[i],points[i+1]
    return a[1]+(b[1]-a[1])*(x-a[0])/(b[0]-a[0])


def sherd(skin,lod):
    # Cut from the ash plate's rim. The old lip survives on one side only.
    profile=dish_section(lod)
    rim=next(j for j,p in enumerate(profile) if p[0]==13.51)
    below=[(r,z) for r,z,_,_ in profile[12:rim+1]]
    above=[(r,z) for r,z,_,_ in reversed(profile[rim:])]
    outline=[(0,9.32),(.09,8.88),(.17,8.94),(.25,8.07),(.38,7.75),(.49,6.67),
             (.57,7.05),(.70,7.11),(.79,7.94),(.86,8.15),(.93,9.03),(1,9.23)]
    n=(36,24,12)[lod]
    radii=[9.90,10.45,11.04,11.56,11.78,11.88,12.04,12.18,12.29,12.45,12.68,12.94,13.18,13.35]
    top,base,outer=[],[],[]
    for j in range(n+1):
        t=j/n
        inner=interp(outline,t)+.085*sin(79*t+.4)
        samples=[inner,(inner+9.90)*.5]+radii
        tr,br=[],[]
        for r in samples:
            x=(r-inner)/(13.51-inner)
            angle=(-.67+1.38*t + (1-t)**5*(.078*sin(r*2.55)+.045*cos(r*5.0)-.18*(1-x))
                   + t**5*(.096*sin(r*2.04+.9)-.045*cos(r*3.65)+.18*(1-x)))
            mark="reed" if r in (11.78,11.88,12.04) else ""
            tr.append(skin.point(*plate_point(r,interp(above,r),angle,mark)))
            br.append(skin.point(*plate_point(r,interp(below,r),angle)))
        top.append(tr)
        base.append(br)
        outer.append(skin.point(*plate_point(13.51,3.16,angle)))
    count=len(top[0])
    for j in range(n):
        for k in range(count-1):
            ids=[top[j][k],top[j][k+1],top[j+1][k+1],top[j+1][k]]
            slot=HONEY if k>=2 and radii[k-2] in (11.78,12.18) else ASH
            skin.face(ids,flat_uv(skin,ids),slot)
            ids=[base[j+1][k],base[j+1][k+1],base[j][k+1],base[j][k]]
            skin.face(ids,flat_uv(skin,ids),ASH)
        for low,high in (([r[-1] for r in base],outer),(outer,[r[-1] for r in top])):
            ids=[low[j],low[j+1],high[j+1],high[j]]
            skin.face(ids,[(j/n,0),((j+1)/n,0),((j+1)/n,.055),(j/n,.055)],ASH)
    # Across the three damaged edges the clay body cleaves at a different angle
    # from its glaze. An off-centre core ridge catches the light along the break.
    edge=([(0,k) for k in range(count-1,-1,-1)] +
          [(j,0) for j in range(1,n+1)]+[(n,k) for k in range(1,count)])
    ridge=[]
    for i,(j,k) in enumerate(edge):
        u,l=skin.points[top[j][k]],skin.points[base[j][k]]
        w=.41+.17*sin(i*5.2)
        x,y,z=[(1-w)*lo+w*hi for lo,hi in zip(l,u)]
        if i in (0,len(edge)-1):
            ridge.append(outer[j])
        else:
            ridge.append(skin.point(x+.115*sin(i*6.9),y+.095*cos(i*4.82),z+.044*sin(i*3.90)))
    for i,((j,k),(jj,kk)) in enumerate(zip(edge,edge[1:])):
        for a,b,c,d in ((base[j][k],base[jj][kk],ridge[i+1],ridge[i]),
                         (ridge[i],ridge[i+1],top[jj][kk],top[j][k])):
            ids=[a,d,c,b]
            skin.face(ids,[(i*.09,0),(i*.09,.07),((i+1)*.09,.07),((i+1)*.09,0)],CLAY,False)
    bounds=list(zip(*skin.points))
    cx,cy=(.5*(min(axis)+max(axis)) for axis in bounds[:2])
    floor=min(bounds[2])
    skin.points=[(x-cx,y-cy,z-floor) for x,y,z in skin.points]


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version=0
    for name,rgb in ((CLAY,(.32,.123,.058)),(ASH,(.53,.43,.29)),
                     (HONEY,(.34,.151,.042)),(OLIVE,(.114,.138,.066))):
        bpy.data.materials.new(name).diffuse_color=(*rgb,1.)
    for index,role in enumerate(("Pitcher","Tankard","Dish","Sherd")):
        name="SM_Tavern"+role
        group=bpy.data.objects.new(name+"_LODs",None)
        group["fbx_type"]="LodGroup"
        bpy.context.collection.objects.link(group)
        children=[]
        for level in range(3):
            skin=Skin()
            if role=="Dish":
                dish(skin,level)
            elif role=="Sherd":
                sherd(skin,level)
            else:
                construct_vessel(skin,role,level)
            obj=skin.mesh_object(name+"_LOD"+str(level))
            obj.modifiers.new("Game triangles","TRIANGULATE")
            obj.parent=group
            children.append(obj)
        bpy.ops.object.select_all(action="DESELECT")
        for obj in [group]+children:
            obj.select_set(True)
        bpy.ops.export_scene.fbx(filepath=str(OUT/(name+".fbx")),use_selection=True,
            object_types={"EMPTY","MESH"},axis_forward="-Y",axis_up="Z",mesh_smooth_type="FACE",
            use_tspace=True,bake_anim=False,use_custom_props=True,add_leaf_bones=False)
        group.location=(index*.36,0,0)
        for obj in children[1:]:
            obj.hide_set(True)
    sys.path.insert(0,str(HERE.parent/"Service"))
    from source_surfaces import bind_service_surfaces
    bind_service_surfaces(SERVICE)
    for img in bpy.data.images:
        if img.source=="FILE" and img.filepath.startswith("//"):
            img.filepath="//../Service/"+img.filepath[2:]
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"TavernStoneware.blend"),relative_remap=False)


if __name__=="__main__":
    build()
