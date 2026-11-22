"""Closed timber and ribbon geometry. Model inputs are in UE centimetres."""
import math
import bpy
from mathutils import Vector

PALETTE = {'Sawn':(.52,.33,.16), 'Oak':(.28,.17,.08), 'Endgrain':(.52,.38,.22),
           'Bark':(.18,.12,.075), 'Peel':(.68,.49,.28)}

class SurfaceMesh:
    def __init__(self, level):
        self.level = level
        self.verts, self.faces, self.attributes, self.slots = [], [], [], []

    def vertices(self, points):
        start = len(self.verts)
        self.verts.extend((x*.01,-y*.01,z*.01) for x,y,z in points)
        return start

    def face(self, indices, uv, material, smooth=False):
        if material not in self.slots:
            self.slots.append(material)
        # Mirror handedness together with winding and face-varying UVs.
        self.faces.append(tuple(reversed(indices)))
        self.attributes.append((self.slots.index(material), tuple(reversed(uv)), smooth))

    def object(self, name):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.verts, [], self.faces)
        mesh.update()
        for slot in self.slots:
            mat = bpy.data.materials.get(slot) or bpy.data.materials.new(slot)
            mat.diffuse_color = (*PALETTE[slot],1.)
            mesh.materials.append(mat)
        layer = mesh.uv_layers.new(name='Cut direction')
        for poly,(material, coords, smooth) in zip(mesh.polygons,self.attributes):
            poly.material_index, poly.use_smooth = material, smooth
            for loop, uv in zip(poly.loop_indices,coords):
                layer.data[loop].uv = uv
        obj = bpy.data.objects.new(name,mesh)
        bpy.context.collection.objects.link(obj)
        return obj

    def board(self,rng,c,length,width,thickness,yaw=0,material='Sawn',wane=0,check=False,tilt=0):
        # Long grain follows each flitch. A drying check opens at the cut end and
        # narrows until it pinches shut. Its two inner faces are real geometry.
        w,h = width*.5,thickness*.5
        b = min(.28,thickness*.10,width*.09)
        notch = rng.uniform(-.31,.31)*width
        seed = rng.uniform(0,6.28)
        phase = rng.random()
        end_shift = rng.uniform(-.014,.014)*length
        heart_y,heart_z = rng.uniform(-.18,.18),rng.uniform(-.17,.17)
        yaw,tilt = math.radians(yaw), math.radians(tilt)
        def world(x,y,z):
            xp = x*math.cos(tilt)-z*math.sin(tilt)
            return (c[0]+xp*math.cos(yaw)-y*math.sin(yaw),
                    c[1]+xp*math.sin(yaw)+y*math.cos(yaw),
                    c[2]+x*math.sin(tilt)+z*math.cos(tilt))
        ts = ((0,.045,.16,.37,.62,.84,.96,1), (0,.13,.48,.86,1), (0,.19,1))[self.level]
        rows, ys_zs = [], []
        for t in ts:
            # Vary side edges only: the top and bottom faces bear on the stickers.
            wave = math.sin(t*math.pi)*math.sin(7*t+seed)
            right = w + wane*(.26*wave-.32)
            left = -w + wane*.12*math.sin(t*4+seed)
            crown = min(thickness*.56,.24+wane*(.62+.17*math.sin(5*t+seed)))
            edge = min(width*.14,b+wane*(.42+.12*wave))
            ring = [(left+b,-h),(right-b,-h),(right,-h+b),(right,h-crown),
                    (right-edge,h)]
            if check:
                amount = max(0,1-t/.16)
                gap = .003 + min(.31,width*.018)*amount
                depth = .008+thickness*.63*amount
                ring.extend([(notch+gap,h),(notch,h-depth),(notch-gap,h)])
            ring.extend([(left+b,h),(left,h-b),(left,-h+b)])
            points = []
            for j,(y,z) in enumerate(ring):
                x = (t-.5)*length + (1-t)*end_shift*y/max(w,.1)
                if j in (2,3,4):
                    x += (1-t)**8 * wane * math.sin(j*1.8+seed)
                points.append(world(x,y,z))
            rows.append(self.vertices(points))
            ys_zs.append(ring)
        n = len(ys_zs[0])
        def perimeter(points):
            values=[0.]
            for j,p in enumerate(points):
                q = points[(j+1)%n]
                values.append(values[-1]+math.dist(p,q))
            return values
        for i in range(len(ts)-1):
            a,b = rows[i:i+2]
            u,v = perimeter(ys_zs[i]),perimeter(ys_zs[i+1])
            for j in range(n):
                k=(j+1)%n
                surf = 'Bark' if wane>=1.5 and j in (2,3) else material
                self.face((a+j,a+k,b+k,b+j),
                          [(phase+val/72,phase+t*length/72) for val,t in
                           ((u[j],ts[i]),(u[j+1],ts[i]),(v[j+1],ts[i+1]),(v[j],ts[i+1]))],surf)
        for i in (0,-1):
            order = list(reversed(range(n))) if i==0 else list(range(n))
            self.face([rows[i]+j for j in order],
                      [(.5+heart_y+ys_zs[i][j][0]/max(43.,width*1.6),
                        .5+heart_z+ys_zs[i][j][1]/max(43.,width*1.6)) for j in order],'Endgrain')

    def splinter(self,c,heading,length,width,height,material,phase,place):
        shape=[(-.54,-.14,.04),(-.31,-.48,.02),(.32,-.36,0),(.5,.13,.02),(-.09,.48,0),
               (-.19,.03,1),(.27,.04,.36)]
        faces=[(0,1,5),(1,2,6,5),(2,3,6),(3,4,5,6),(4,0,5),(4,3,2,1,0)]
        ca,sa=math.cos(heading),math.sin(heading)
        pts=[(c[0]+ca*x*length-sa*y*width,c[1]+sa*x*length+ca*y*width,z*height) for x,y,z in shape]
        start=self.vertices(place(pts))
        for ids in faces:
            self.face([start+i for i in ids],[(phase+shape[i][1]*width/24,phase+shape[i][0]*length/24) for i in ids],material)

    def ribbon(self,c,yaw,turns,radius,width,travel,phase,hand,place):
        # A tapering helical shaving, curled across the grain, with a crowned
        # section and a torn lip. UV length is the unwound length of the strip.
        count=max(9,math.ceil(turns*(29,17,10)[self.level]))
        ca,sa=math.cos(yaw),math.sin(yaw)
        points,uv=[],[]
        length,last=0,None
        for j in range(count+1):
            t=j/count
            a=phase+hand*math.tau*turns*t
            rad=radius*(.42+.95*t+.13*math.sin(t*math.pi*2+phase))
            center=Vector((travel*(t-.5),rad*math.cos(a),rad*math.sin(a)))
            if last is not None: length+=(center-last).length
            last=center.copy()
            breadth=width*(.32+.68*math.sin(math.pi*(.08+.86*t))**.7)
            skew=.16*math.sin(t*5+phase)
            # Start at the underside, then the upper three rails, back around the edge.
            for across,thick in [(-.5,-.055),(0,-.055),(.5,-.055),(.5,.055),(0,.055),(-.5,.055)]:
                edge=across*breadth*(1+.065*math.sin(12*t+phase+across*3))
                sag=breadth*.052*(1-4*across*across)
                off=thick+sag
                arc=edge*skew + (1-t)**9*edge*.25
                x=center.x+edge
                y=center.y+off*math.cos(a)-arc*math.sin(a)
                z=center.z+off*math.sin(a)+arc*math.cos(a)
                points.append((c[0]+ca*x-sa*y,c[1]+sa*x+ca*y,z))
                uv.append((phase+edge/42.,phase+length/42.))
        start=self.vertices(place(points))
        for j in range(count):
            for k in range(6):
                nxt=(k+1)%6
                ids=(j*6+k,(j+1)*6+k,(j+1)*6+nxt,j*6+nxt)
                # Outward top/bottom normals follow the direction of winding.
                if hand>0: ids=ids[::-1]
                self.face([start+i for i in ids],[uv[i] for i in ids],'Peel', k in (0,1,3,4))
        for j in (0,count):
            ids=[j*6+k for k in range(6)]
            if (j==0)==(hand<0): ids.reverse()
            self.face([start+i for i in ids],[(phase+k/40, .4+(.01 if k>=3 else 0)) for k in range(6)],'Peel')
