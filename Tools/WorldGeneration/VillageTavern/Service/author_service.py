"""Turned stoneware and cooperage for the hillside inn. Profile dimensions in cm."""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parents[4] / "SourceAssets/HillsVillageTavern/Service"
OUT.mkdir(exist_ok=True, parents=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
materials = {}
for name, rgb in (("Clay", (.39,.19,.10)), ("OliveGlaze", (.21,.26,.13)),
                  ("HoneyGlaze", (.48,.25,.075)), ("AshGlaze", (.53,.46,.31)),
                  ("Oak", (.21,.14,.075)), ("Endgrain", (.34,.22,.12)), ("Iron", (.12,.12,.12))):
    materials[name] = bpy.data.materials.new(name)
    materials[name].diffuse_color = (*rgb, 1)


class Surface:
    def __init__(self):
        self.verts, self.faces, self.loops, self.slots, self.smooth = [], [], [], [], []

    def face(self, indices, uv, slot, smooth):
        self.faces.append(indices)
        self.loops.append(uv)
        self.slots.append(slot)
        self.smooth.append(smooth)

    def lathe(self, profile, segments, textured, angular=(0, math.tau), offset=(0,0,0),
              handmade=0., sector_ends=False, lip=False, fracture=False):
        """Closed section revolves from the foot, up the outside, and back inside."""
        idx = len(self.verts)
        full = abs(angular[1] - angular[0] - math.tau) < 1e-6
        stride = segments if full else segments + 1
        for row,(r, z, mat) in enumerate(profile):
            for i in range(stride):
                a = angular[0] + (angular[1] - angular[0]) * i / segments
                if fracture:
                    # Deviate at both breaks, fading towards the untouched inner part of the rim.
                    t=i/segments
                    a += (1-t)**4*(.043*(r-11.4)+.053*math.sin(2*r)) + t**4*(.032*(r-12)-.041*math.sin(2.2*r))
                rr = r * (1 + handmade * (.5*math.sin(3*a+.21*z)+.3*math.sin(5*a+.12*z)))
                rise = 0.
                if full and handmade and z>2. and mat!="Clay" and profile[row-1][2]=="Clay":
                    rise=.27*math.sin(a*3+.8)+.11*math.sin(a*7)-.16*max(0.,math.cos(2*a))**5
                if fracture and (row==0 or row==len(profile)-1):
                    t=i/segments
                    rr -= .25+.56*abs(math.sin(4*math.pi*t+.8))+.25*math.cos(7*math.pi*t)
                if lip and z > 18:
                    spout = max(0., math.cos(a - math.pi))**20
                    t = min(1., (z-18)/4)
                    rr += 1.55*t*spout
                    rise = .55*t*spout
                self.verts.append(((offset[0]+rr*math.cos(a))/100,
                                   (offset[1]+rr*math.sin(a))/100,(offset[2]+z+rise)/100))
        for j, (r, z, mat) in enumerate(profile):
            jj = (j+1) % len(profile)
            if jj == 0 and full and profile[0][0] < 1 and profile[-1][0] < 1:
                for row in (0,j):
                    ids=[idx+row*stride+i for i in range(stride)]
                    if row==0: ids.reverse()
                    self.face(ids,[(self.verts[q][0]*2+.5,self.verts[q][1]*2+.5) for q in ids],profile[row][2],False)
                continue
            r2,z2,_ = profile[jj]
            for i in range(segments):
                k = (i+1) % stride
                ids = [idx+j*stride+i,idx+j*stride+k,idx+jj*stride+k,idx+jj*stride+i]
                if mat == "Endgrain" or (not textured and abs(r-r2)>abs(z-z2)*1.3):
                    uv = [(self.verts[q][0]*2+.5,self.verts[q][1]*2+.5) for q in ids]
                else:
                    def coord(h, radius, angle):
                        return (angle*(.5*(r+r2))/32, h/32) if textured else (angle/math.tau, (h+radius*.09)/25)
                    a0=angular[0]+(angular[1]-angular[0])*i/segments
                    a1=angular[0]+(angular[1]-angular[0])*(i+1)/segments
                    uv=[coord(z,r,a0),coord(z,r,a1),coord(z2,r2,a1),coord(z2,r2,a0)]
                self.face(ids,uv,mat,not textured and abs(z2-z)+abs(r2-r)>.01)
        if sector_ends:
            for cap in (0, segments):
                ids = [idx+j*stride+cap for j in range(len(profile))]
                if cap == segments: ids.reverse()
                self.face(ids,[(r/32,z/32) for r,z,_ in (profile[::-1] if cap==segments else profile)],"Clay" if fracture else profile[0][2],False)

    def prism(self, polygon, low, high, face_slot="Oak", edge_slot="Oak"):
        # CCW outline in centimetres, with continuous long-grain UVs across each board face.
        idx=len(self.verts)
        count=len(polygon)
        for z in (low,high):
            self.verts.extend((x/100,y/100,z/100) for x,y in polygon)
        for layer in (0,1):
            order=list(range(count)) if layer else list(reversed(range(count)))
            self.face([idx+layer*count+i for i in order],
                      [(polygon[i][0]/34,polygon[i][1]/70) for i in order],face_slot,False)
        for i,(x,y) in enumerate(polygon):
            k=(i+1)%count
            length=math.dist((x,y),polygon[k])
            self.face([idx+i,idx+k,idx+count+k,idx+count+i],
                      [(0,0),(length/58,0),(length/58,(high-low)/34),(0,(high-low)/34)],edge_slot,False)

    def handle(self, path, slot, sides=12):
        # Oval strap handle with thick roots fused inside the vessel wall.
        start = len(self.verts)
        for j,(x,z,wide,thick) in enumerate(path):
            before = path[max(0,j-1)]
            after = path[min(j+1,len(path)-1)]
            tangent = Vector((after[0]-before[0],after[1]-before[1])).normalized()
            for k in range(sides):
                a = math.tau*k/sides
                dx,dz = tangent.y*math.cos(a)*thick,-tangent.x*math.cos(a)*thick
                self.verts.append(((x+dx)/100,wide*math.sin(a)/100,(z+dz)/100))
        for j in range(len(path)-1):
            for i in range(sides):
                k=(i+1)%sides
                self.face([start+j*sides+i,start+j*sides+k,start+(j+1)*sides+k,start+(j+1)*sides+i],
                          [(i/sides,j/8),((i+1)/sides,j/8),((i+1)/sides,(j+1)/8),(i/sides,(j+1)/8)],slot,True)

    def object(self, name):
        mesh=bpy.data.meshes.new(name)
        mesh.from_pydata(self.verts, [], self.faces)
        mesh.update()
        names=list(dict.fromkeys(self.slots))
        for slot in names: mesh.materials.append(materials[slot])
        uv=mesh.uv_layers.new(name="SurfaceUV")
        for poly,slot,coords,smooth in zip(mesh.polygons,self.slots,self.loops,self.smooth):
            poly.material_index=names.index(slot)
            poly.use_smooth=smooth
            for loop,coord in zip(poly.loop_indices,coords): uv.data[loop].uv=coord
        obj=bpy.data.objects.new(name,mesh)
        bpy.context.collection.objects.link(obj)
        return obj


def crock(s, shape, glaze, sides, **kwargs):
    s.lathe([(max(.65,r),z,glaze if glazed else "Clay") for r,z,glazed in shape],sides,False,handmade=.012,**kwargs)


def cup(s,n):
    crock(s,[(.05,.25,0),(3.4,.25,0),(3.55,0,0),(4,0,0),(4.18,.28,0),(4.18,.85,0),
             (4.1,1.25,0),(4.72,3,1),(5.05,7.9,1),(5.08,9.35,1),(5.22,9.65,1),
             (5.21,10.02,1),(5.03,10.23,1),(4.7,10.21,1),(4.52,9.9,1),
             (4.51,8.95,1),(4.04,3,1),(3.72,1.32,1),(.05,1.22,1)], "OliveGlaze",n)
    s.handle([(4.55,8.4,1.35,.71),(5.1,8.8,1.28,.70),(6.30,9.02,1.06,.69),
              (7.32,8.69,.94,.69),(7.88,7.78,.91,.75),(7.80,6.35,.88,.74),
              (7.24,4.82,.89,.71),(6.38,3.70,.96,.68),(5.20,3.16,1.16,.70),(4.45,3.25,1.34,.74)],"OliveGlaze")


def jug(s,n):
    crock(s,[(.05,.4,0),(4.6,.4,0),(4.75,0,0),(5.46,0,0),(5.7,.5,0),(5.63,1.28,0),
             (6.2,2.7,0),(7.53,5.55,1),(8.3,8.7,1),(8.25,11.7,1),(7.65,14.7,1),
             (6.52,16.48,1),(4.78,18.1,1),(4.61,19,1),(4.65,20.15,1),(5.31,21.9,1),
             (5.55,22.3,1),(5.52,22.7,1),(5.20,22.92,1),(4.87,22.69,1),(4.02,20.2,1),
             (4.03,18.5,1),(5.8,16.2,1),(7.52,11.4,1),(7.49,8.62,1),(5.46,3.1,1),(.05,1.64,1)],"HoneyGlaze",n,lip=True)
    s.handle([(4.46,19.55,1.58,.95),(5.48,20.04,1.48,.86),(7.42,20.45,1.17,.82),
              (9.23,19.26,1.08,.87),(10.45,17.04,1.05,.93),(10.50,14.63,1.04,.88),
              (9.88,12.28,1.09,.82),(8.56,10.24,1.32,.87),(7.76,9.82,1.55,.92)],"HoneyGlaze")


def plate(s,n,shard=False):
    shape=[(.05,.58,0),(4.9,.58,0),(5.25,.08,0),(5.67,0,0),(5.98,.08,0),
           (6.22,.57,0),(10.1,1.16,1),(12.15,2.03,1),(13.43,2.62,1),
           (13.54,2.91,1),(13.29,3.11,1),(12.9,3.08,1),(10.98,2.34,1),(8.9,1.67,1),(.05,1.25,1)]
    if shard:
        # A separated chipped rim, exposing the unglazed body on its fracture.
        crock(s,shape[6:12]+[(10.68,2.21,0)],"AshGlaze",max(7,n//4),
              angular=(.25,1.86),sector_ends=True,fracture=True,offset=(0,0,-1.16))
    else: crock(s,shape,"AshGlaze",n)


def cask(s,n):
    nstaves=18
    outline=[(25.1,0),(26.25,.8),(27.3,6),(30.4,21),(31.25,35),(30.85,48),(28.7,61),(26.0,70),(25.3,71)]
    for i in range(nstaves):
        a=math.tau*i/nstaves
        a1=math.tau*(i+1)/nstaves
        profile=[(r,z,"Oak") for r,z in outline]+[(23.5,71,"Endgrain"),(23.6,68,"Oak"),(23.6,.35,"Endgrain")]
        s.lathe(profile,max(2,n//18),True,(a+.0016,a1-.0016),sector_ends=True)
    def stave_radius(z):
        for (r0,z0),(r1,z1) in zip(outline,outline[1:]):
            if z0<=z<=z1: return r0+(r1-r0)*(z-z0)/(z1-z0)
    for z,h in ((4.3,3.15),(15.5,3.5),(54.8,3.5),(65,3.15)):
        r=stave_radius(z)
        dr=(stave_radius(z+h)-r)/h
        s.lathe([(r-.4,z,"Iron"),(r+.34,z,"Iron"),(r+.46,z+.26,"Iron"),
                 (r+.46+dr*h,z+h-.25,"Iron"),(r+.32+dr*h,z+h,"Iron"),(r-.44+dr*h,z+h,"Iron")],n,True)
    # Recess both heads inside the croze. Straight seams and grain follow the actual head boards.
    radius=24.35
    board_edges=(-radius,-15.2,-5.7,4.2,14.6,radius)
    for lo,hi in zip(board_edges,board_edges[1:]):
        left=lo+.059
        right=hi-.059
        xs=[left]+[radius*math.cos(math.pi*j/max(12,n//2)) for j in range(max(12,n//2)-1,0,-1)
                   if left+.05<radius*math.cos(math.pi*j/max(12,n//2))<right-.05]+[right]
        arc=[(x,math.sqrt(max(0.,radius**2-x**2))) for x in xs]
        polygon=[(x,-y) for x,y in arc]+list(reversed(arc))
        for z in (1.7,66.45):
            s.prism(polygon,z,z+1.7,"Oak","Endgrain")
    s.lathe([(.7,-.3,"Endgrain"),(2.9,-.3,"Oak"),(3.08,.34,"Oak"),
             (2.84,.47,"Endgrain"),(.7,.47,"Endgrain")],max(14,n//2),True,offset=(8.1,-7.2,68.15))


def tap_cask(s,n):
    cask(s,n)
    # Tilt the barrel onto two notched bearers. Local +X is the serving face.
    s.verts=[(z-.355,y,.79-x) for x,y,z in s.verts]
    def plank(x,y,w,d,z,h):
        s.prism([(x-w/2,y-d/2),(x+w/2,y-d/2),(x+w/2,y+d/2),(x-w/2,y+d/2)],z,z+h)
    for x in (-21.,21.):
        for y in (-22.,22.): plank(x,y,6.5,7.,0.,50.)
        plank(x,0.,5.,38.,14.,6.)
        first=len(s.verts)
        ys=(27.,25.,21.,16.,10.,4.,0.,-4.,-10.,-16.,-21.,-25.,-27.)
        saddle=[(-28.,42.),(28.,42.),(28.,68.)]+[(y,79.-math.sqrt(29.65**2-y*y)) for y in ys]+[(-28.,68.)]
        s.prism(saddle,-3.8,3.8)
        s.verts[first:]=[(x/100+c,a,b) for a,b,c in s.verts[first:]]
    for y in (-22.,22.): plank(0.,y,36.5,5.,36.,8.)
    # Peg tap has a tapered body, downward outlet and transverse hand lever.
    def turning(profile,axis,at):
        first=len(s.verts)
        s.lathe([(r,z,"Oak") for r,z in profile],max(12,n//3),True)
        for i,(a,b,c) in enumerate(s.verts[first:],first):
            if axis=="X": a,b,c=c,b,-a
            elif axis=="Y": a,b,c=a,c,-b
            s.verts[i]=(a+at[0]/100,b+at[1]/100,c+at[2]/100)
    turning([(.66,0),(2.7,0),(2.9,2),(2.4,3),(1.7,12),(1.8,15.7),(.66,16)],"X",(32.,0.,64.))
    turning([(.8,0),(1.38,0),(1.44,3),(1.65,6.3),(.8,6.6)],"Z",(45.,0.,57.8))
    turning([(.7,0),(1.,0),(.92,6),(.7,6.2)],"Z",(43.,0.,64.8))
    turning([(.64,0),(1.03,.4),(1.12,1.2),(.85,4),(.87,7.5),(1.17,8.4),(.7,9)],"Y",(43.,-4.5,70.4))


for index,(name,build) in enumerate((("Tankard",cup),("Pitcher",jug),("Dish",plate),("Sherd",lambda s,n:plate(s,n,True)),("AleCask",cask),("TapCask",tap_cask))):
    asset="SM_Tavern"+name
    group=bpy.data.objects.new(asset+"_LODs",None)
    group["fbx_type"]="LodGroup"
    bpy.context.collection.objects.link(group)
    children=[]
    for level,segments in enumerate((72,36,18)):
        surface=Surface()
        build(surface,segments)
        obj=surface.object(asset+"_LOD"+str(level))
        obj.modifiers.new("Game triangles","TRIANGULATE")
        obj.parent=group
        children.append(obj)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [group]+children: obj.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT/(asset+".fbx")),use_selection=True,
        object_types={"EMPTY","MESH"},axis_forward="-Y",axis_up="Z",mesh_smooth_type="FACE",
        use_tspace=True,bake_anim=False,use_custom_props=True,add_leaf_bones=False)
    group.location=(index*.9,0,0)
    for obj in children[1:]: obj.hide_set(True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from source_surfaces import bind_service_surfaces
bind_service_surfaces(OUT)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"TaproomService.blend"),relative_remap=False)
