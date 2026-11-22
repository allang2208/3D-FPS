"""Counter glazing, folded-sheet shop fittings and small forged hardware."""
from math import cos, pi, sin
from shell_geometry import Mesh, cross, mean, sub, unit


def pin(mesh, material, a, b, radius, sides=12):
    direction = unit(sub(b, a))
    side = unit(cross(direction,(0,0,1) if abs(direction[2])<.92 else (0,1,0)))
    up = unit(cross(direction,side))
    face = [tuple(a[i]+radius*(side[i]*cos(2*pi*k/sides)+up[i]*sin(2*pi*k/sides))
                  for i in range(3)) for k in range(sides)]
    mesh.prism(material,face,sub(b,a))


def fitting_mesh():
    return Mesh()


GLYPHS = {
    'A':('01 15 21','04 24'), 'K':('00 05','25 02 20'), 'M':('00 05 13 25 20',),
    'S':('25 05 03 23 20 00',), 'U':('05 01 10 21 25',), 'P':('00 05 25 23 03',),
    'E':('25 05 00 20','03 23'), 'R':('00 05 25 23 03 20',),
    'O':('01 04 15 24 21 10 01',), 'T':('05 25','15 10'), 'I':('05 25','15 10','00 20'),
    'C':('24 15 04 01 10 21',), '0':('01 04 15 24 21 10 01',),
    '1':('04 15 10','00 20'), '2':('04 15 24 23 00 20',),
    '6':('25 15 04 01 10 21 23 03',), '9':('20 24 15 04 02 22',),
}


def stamped_label(m, word, x, y, z, height):
    # The enamel is clipped to its brass backing. Individual stamped strokes
    # are raised on the face, independent of the texel density on the rack.
    unit=height/5.
    width=(len(word)*3.8+3.0)*unit
    m.box('Brass',x-width/2,x+width/2,y-.46,y+.24,z-.7,z+height+.7,.17)
    m.box('Enamel',x-width/2+.25,x+width/2-.25,y-.54,y-.46,z-.47,z+height+.47,.11)
    start=x-((len(word)-1)*3.8+2)*.5*unit
    for i,letter in enumerate(word):
        for stroke in GLYPHS[letter]:
            coordinates=[(start+(i*3.8+int(t[0]))*unit,y-.60,z+int(t[1])*unit) for t in stroke.split()]
            for a,b in zip(coordinates,coordinates[1:]):
                pin(m,'Brass',a,b,unit*.16,6)


def board():
    m = Mesh()
    # A closed ring around each through-hole; the shared square cell boundary has
    # no interior walls. Outer return folds and standoffs expose the air gap on edge.
    pitch = 6.
    for column in range(20):
        x = -57.+column*pitch
        for row in range(14):
            z = 3.+row*pitch
            front, rear, mouth, throat = [], [], [], []
            for i in range(12):
                a = (i*30+15)*pi/180.
                c,s = cos(a),sin(a)
                f = 3./max(abs(c),abs(s))
                front.append((x+c*f,-.28,z+s*f))
                rear.append((x+c*f,.28,z+s*f))
                mouth.append((x+c*.86,-.28,z+s*.86))
                throat.append((x+c*.72,.28,z+s*.72))
            for i in range(12):
                j = (i+1)%12
                # face centers prescribe winding and normals even around the inner lip.
                m.face('Enamel',[front[i],front[j],mouth[j],mouth[i]],(x,1,z))
                m.face('Enamel',[rear[i],throat[i],throat[j],rear[j]],(x,-1,z))
                polygon=[mouth[i],mouth[j],throat[j],throat[i]]
                ctr=mean(polygon)
                m.face('Iron',polygon,(2*ctr[0]-x,ctr[1],2*ctr[2]-z))
    # The outline of each cell is twelve sided with exact corners at 45/135/225/315.
    for x in (-60.,60.):
        m.box('Enamel',x-.4,x+.4,-.25,3.5,0,84,.15)
        m.box('Oak',x-2.2,x+2.2,3.5,10,2,82,.6)
    for z in (0.,84.):
        m.box('Enamel',-60,60,-.28,3.5,z-.32,z+.32,.14)
        m.box('Oak',-62.5,62.5,2.9,10,z-2.1,z+2.1,.8)
    for x in (-55.,55.):
        for z in (4.,80.):
            pin(m,'Steel',(x,-.3,z),(x,-1.15,z),1.12)
            m.box('Iron',x-.64,x+.64,-1.25,-1.12,z-.12,z+.12,.06)
    return m


def shelf(m,x,z):
    # Folded brackets sit behind the part and emerge through the panel.
    for dx in (-10.,10.):
        m.box('Steel',x+dx-.64,x+dx+.64,-17.6,-.45,z-1.8,z-.58,.18)
        m.prism('Enamel',[(x+dx-.55,-1,z-8.5),(x+dx-.55,-16,z-1.65),
                           (x+dx-.55,-1,z-1.65)],(1.1,0,0))
        pin(m,'Steel',(x+dx,1.,z-5),(x+dx,-1.3,z-5),1.05)
    m.box('Enamel',x-19,x+19,-24,-.65,z-.6,z,.45)
    m.box('Enamel',x-19,x+19,-24,-23.48,z-.6,z+1.35,.16)
    # A small buff insert in a folded brass holder below the shelf lip.
    m.box('Brass',x-4.2,x+4.2,-24.2,-23.7,z-2.1,z+.95,.18)
    m.box('Linen',x-3.3,x+3.3,-24.30,-24.2,z-1.65,z+.42,.10)


def panels(optics):
    m=Mesh()
    for x,z in [(-27.,28.),(-27.,58.),(25.,58.)]+([] if optics else [(25.,28.)]):
        shelf(m,x,z)
    # J-pegs occupy selected spare holes with two bends and a turned-up tip.
    for x,z in ([(21,21),(33,21),(21,33)] if optics else [(-9,45),(3,45)]):
        pin(m,'Steel',(x,1.,z+6),(x,-1.4,z+6),.57)
        pin(m,'Steel',(x,-1.4,z+6),(x,-1.4,z),.57)
        pin(m,'Steel',(x,-1.4,z),(x,-12.,z),.57)
        pin(m,'Steel',(x,-12.,z),(x,-13.3,z+2.3),.57)
    stamped_label(m,'OPTICS' if optics else 'PARTS',0,-.46,73,3.3)
    return m


def drawers():
    m=Mesh()
    # Separate framed carcass, working toe recess, individual inset drawer faces
    # with penumbras, bailed handles, tiny screws and hand-written card holders.
    for x in (-67.,67.):
        m.box('Oak',x-2.1,x+2.1,-22,22,0,87,.7)
    m.box('DarkWood',-65,65,-15,21,3,11,.8)
    m.box('Oak',-67,67,-21,21,11,85,.8)
    m.box('Sawn',-70,70,-23,23,85,90,1.1)
    for r in range(3):
        for c in range(4):
            x=-49.5+33*c
            z=14+23*r
            m.box('DarkWood',x-16.25,x+16.25,-21.7,-20.5,z,z+20.8,.4)
            m.box('Oak',x-15.35,x+15.35,-22.7,-21.7,z+.85,z+19.9,.8)
            m.box('Brass',x-4.4,x+4.4,-23.24,-22.7,z+12.8,z+16.8,.15)
            m.box('Linen',x-3.8,x+3.8,-23.32,-23.24,z+13.3,z+16.3,.08)
            for dx in (-4.,4.):
                pin(m,'Iron',(x+dx,-22.7,z+7),(x+dx,-24.4,z+7),1.2)
                pin(m,'Brass',(x+dx,-24.1,z+7),(x+dx,-26.1,z+5.4),.55)
            pin(m,'Brass',(x-4.,-26.1,z+5.4),(x+4.,-26.1,z+5.4),.64)
    return m


def sample_case():
    m=Mesh()
    for x in (-31.,31.):
        for y in (-15.,15.):
            m.box('Rubber',x-2,x+2,y-2,y+2,0,1.1,.7)
    m.box('Oak',-36,36,-18.7,18.7,1.1,4.7,.9)
    m.box('Baize',-34.2,34.2,-17,17,4.7,5.25,1.)
    for x in (-35.3,35.3):
        m.box('Brass',x-.75,x+.75,-18.7,18.7,4.5,5.9,.18)
    for y in (-18.,18.):
        m.box('Brass',-35.3,35.3,y-.7,y+.7,4.5,5.9,.16)
    # Top canopy and four clear vertical panes are physically separated at the corner posts.
    for x in (-35.2,35.2):
        for y in (-17.9,17.9):
            m.box('Brass',x-.68,x+.68,y-.68,y+.68,5.7,21.1,.2)
        m.box('Glass',x-.16,x+.16,-17.23,17.23,5.9,20.45)
    for y in (-17.9,17.9):
        m.box('Glass',-34.52,34.52,y-.16,y+.16,5.9,20.45)
        m.box('Brass',-36,36,y-.58,y+.58,20.45,21.7,.2)
    for x in (-35.2,35.2):
        m.box('Brass',x-.58,x+.58,-17.35,17.35,20.45,21.7,.2)
    m.box('Glass',-34.7,34.7,-17.37,17.37,20.6,20.99)
    m.box('Brass',-2.5,2.5,18.1,19.8,8,11,.45)
    pin(m,'Iron',(0,19.8,9.5),(0,20.,9.5),.55)
    stamped_label(m,'M1911',0,-18.78,1.85,2.1)
    return m


def counter_tray():
    m=Mesh()
    m.box('DarkWood',-26,26,-15,15,0,1.45,1.2)
    m.box('Baize',-24.7,24.7,-13.7,13.7,1.45,1.83,.75)
    # A low customer-side lip leaves the liner visible. A narrow rear well
    # keeps small samples separate from the central inspection surface.
    for x in (-25.35,25.35):
        m.box('Oak',x-.65,x+.65,-14.7,14.7,1.45,3.55,.4)
    for y,height in ((-14.35,2.55),(14.35,3.55)):
        m.box('Oak',-24.7,24.7,y-.65,y+.65,1.45,height,.35)
    m.box('DarkWood',-24.7,24.7,7.8,8.7,1.82,2.85,.2)
    for x in (-22.,22.):
        for y in (-14.35,14.35):
            top=2.55 if y<0 else 3.55
            m.box('Brass',x-1.9,x+1.9,y-.44,y+.44,top,top+.12,.16)
    return m


def rifle_support(m,x,y,z,rail):
    # A backing strap reaches an actual transverse rail even when the two contact
    # heights differ. The sleeved arm follows the underside of the displayed mesh.
    m.box('Iron',x-2.25,x+2.25,10.8,14.5,min(z-3.5,rail-3.2),max(z+3,rail+3.2),.42)
    pin(m,'Steel',(x,10.85,rail),(x,10.10,rail),1.08)
    pin(m,'Iron',(x,11.1,z-.85),(x,y-4.9,z-.85),.83)
    pin(m,'Rubber',(x,y+2.6,z-.85),(x,y-3.7,z-.85),.92)
    pin(m,'Iron',(x,y-4.9,z-.85),(x,y-6.05,z+3.45),.77)
    pin(m,'Rubber',(x,y-6.0,z+3.15),(x,y-6.45,z+4.7),.9)
