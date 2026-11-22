"""One tabletop group, drawn in centimetres around the smith's bench datum."""
from math import cos, radians, sin
from shell_geometry import Mesh, mean


def shoe(mesh, cx, cy, yaw, punched):
    # The open heels taper. Split the web around each square nail hole so the
    # holes go through the stock and show the actual worktop underneath.
    turn = radians(yaw)
    sections = 36

    def point(i, across, z):
        angle = radians(-122 + 244*i/sections)
        width = 1.9 + .65*cos(angle)
        x = (6.5 + width*across)*sin(angle)
        y = (8.4 + width*across)*cos(angle)
        return (cx+x*cos(turn)-y*sin(turn), cy+x*sin(turn)+y*cos(turn), z)

    pierced = {3,7,11,24,28,32} if punched else set()
    bands = (-.5, -.115, .115, .5)
    for i in range(sections):
        for j in range(3):
            if j == 1 and i in pierced:
                continue
            lo, hi = bands[j:j+2]
            corners = [(i,lo),(i+1,lo),(i+1,hi),(i,hi)]
            bottom = [point(k,w,.02) for k,w in corners]
            top = [point(k,w,.82 if punched else .98) for k,w in corners]
            center = mean(bottom+top)
            mesh.face('Iron',bottom,center)
            mesh.face('Iron',top,center)
            sides = (j==0 or (j==2 and i in pierced), i==sections-1 or (j==1 and i+1 in pierced),
                     j==2 or (j==0 and i in pierced), i==0 or (j==1 and i-1 in pierced))
            for k, exposed in enumerate(sides):
                if exposed:
                    n = (k+1)%4
                    mesh.face('Iron',[bottom[k],bottom[n],top[n],top[k]],center)


def model():
    mesh = Mesh()
    shoe(mesh,-10.,1.,-19,True)
    shoe(mesh,9.,4.,26,False)
    # Tapered farrier's nails laid flat, with broad forged heads against the wood.
    for x,y,angle in ((-5,-14,-18),(-2,-16,-8),(3,-13,12),(8,-15,32)):
        a = radians(angle)
        def at(s,w,z):
            return (x+s*cos(a)-w*sin(a),y+s*sin(a)+w*cos(a),z)
        mesh.prism('Iron',[at(0,-.24,.04),at(5.8,0,.04),at(0,.24,.04)],(0,0,.37))
        mesh.prism('Iron',[at(-.68,-.58,.02),at(.12,-.58,.02),at(.12,.58,.02),at(-.68,.58,.02)],(0,0,.72))
    # Wooden rasp handle lies on the back edge with the steel off the seating side.
    mesh.timber('Oak',(-20.,16.,1.14),(-9.8,16.,1.14),2.65,2.2,.48)
    mesh.timber('Iron',(-10.,16.,1.06),(-7.9,16.,1.06),2.1,1.65,.25)
    mesh.timber('Iron',(-8.2,16.,.73),(13.,16.,.52),2.5,.85,.18)
    return mesh
