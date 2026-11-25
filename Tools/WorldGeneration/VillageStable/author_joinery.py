"""Background Blender source for the fitted joinery. Positions are UE centimetres."""
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from stable_profile import roof_top

OUT = Path(__file__).resolve().parents[3] / "SourceAssets/HillsVillageStable/AssemblyR1/Exchange"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.scene.unit_settings.scale_length = .01
rng = random.Random(45118)
vertices, faces, surfaces, uvs = [], [], [], []
slots = []


def prism(a, b, width, depth, material, chamfer=.8, sides=0):
    """Sweep an eight-corner timber section or a round metal/wood pin along its long grain."""
    start, end = Vector(a), Vector(b)
    axis = (end-start).normalized()
    reference = Vector((0,0,1)) if abs(axis.z)<.95 else Vector((0,-1,0))
    side = reference.cross(axis).normalized()
    up = axis.cross(side)
    w,d = width/2,depth/2
    c = min(chamfer,w*.45,d*.45)
    section = [(w-c,d),(-w+c,d),(-w,d-c),(-w,-d+c),(-w+c,-d),(w-c,-d),(w,-d+c),(w,d-c)]
    if sides:
        section = [(w*math.cos(i*math.tau/sides),d*math.sin(i*math.tau/sides)) for i in range(sides)]
    n = len(section)
    base = len(vertices)
    for center in (start,end):
        for s,t in section:
            p = center+s*side+t*up
            vertices.append((p.x,-p.y,p.z))
    if material not in slots:
        slots.append(material)
    def face(indices, uv):
        # Reflected coordinate basis needs reflected winding.
        faces.append([base+i for i in reversed(indices)])
        uvs.extend(reversed(uv))
        surfaces.append(slots.index(material))
    face(list(reversed(range(n))),[(s/100,t/100) for s,t in reversed(section)])
    face(list(range(n,n*2)),[(s/100,t/100) for s,t in section])
    v0 = rng.uniform(.05,.9)
    u0 = rng.uniform(0,1)
    length = (end-start).length/100.
    for i in range(n):
        j = (i+1)%n
        v1 = v0+math.dist(section[i],section[j])/100.
        face([i,j,j+n,i+n],[(u0,v0),(u0,v1),(u0+length,v1),(u0+length,v0)])
        v0=v1


def rail(x1,x2,y,z,d,h,mat):
    prism((x1,y,z),(x2,y,z),d,h,mat)


def post(x,y,z0,z1,w,d,mat):
    prism((x,y,z0),(x,y,z1),w,d,mat)


def pin(x,y,z):
    prism((x,y-1.8,z),(x,y+1.8,z),3.8,3.8,"endgrain",sides=8)


def export(name):
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(vertices,[],faces)
    mesh.update()
    for slot in slots:
        mesh.materials.append(bpy.data.materials.get(slot) or bpy.data.materials.new(slot))
    mesh.polygons.foreach_set("material_index",surfaces)
    layer=mesh.uv_layers.new(name="Grain")
    layer.uv.foreach_set("vector",[v for point in uvs for v in point])
    obj=bpy.data.objects.new("SM_Stable_"+name,mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj
    obj.select_set(True)
    tri=obj.modifiers.new("Triangulated joinery","TRIANGULATE")
    bpy.ops.object.modifier_apply(modifier=tri.name)
    bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+".fbx")),use_selection=True,object_types={"MESH"},
        axis_forward="Y",axis_up="Z",apply_unit_scale=True,apply_scale_options="FBX_SCALE_UNITS",
        mesh_smooth_type="FACE",use_tspace=True,bake_anim=False,path_mode="STRIP")
    bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.meshes.remove(mesh)
    for values in (vertices,faces,surfaces,uvs,slots):
        values.clear()


# Set between bents. A staggered fieldstone plinth supports framed lime infill.
for row in range(3):
    x=-210
    while x<209:
        length=min(210-x,rng.uniform(31,63))
        rail(x+.3,x+length-.3,rng.uniform(-.8,.8),row*12+5.5,24+rng.uniform(-1,2),11.8,"stone")
        x+=length
rail(-211,211,0,43,21,13,"darkwood")
for left,right in ((-208,-63),(-51,51),(63,208)):
    top=198 if left==-51 else 271
    rail(left,right,0,(49+top)/2,14,top-49,"lime")
for x in (-57,57):
    post(x,0,46,282,12,20,"oak")
for sign in (-1,1):
    prism((sign*66,-7,58),(sign*196,-7,262),9,9,"darkwood")
for z in (209,224,239,254,269):
    rail(-52,52,0,z,12,7,"darkwood")
rail(-209,209,0,278,21,14,"oak")
for x in (-185,-57,57,185):
    for z in (43,278): pin(x,-10,z)
export("RearVentWall")

# Fixed partitions beside a 152 cm rear half-door. Rounded, pinned kick boards.
for left,right in ((-215,-76),(76,215)):
    for x in (left+5,right-5):
        post(x,0,0,150,10,13,"oak")
    for z in (28,65,101,138):
        rail(left+8,right-8,0,z,6.5,14,"lightwood")
        for x in (left+12,right-12):pin(x,-3.3,z)
export("RearHalfDoorSides")

# Housed knee braces, a scarfed front plate and forged retaining straps at each seam.
for y in (-399,399):
    prism((0,y,226),(0,y-math.copysign(59,y),286),11,12,"oak")
    for x in (-1,1):
        prism((0,y,244),(x*54,y,290),10,11,"oak")
        pin(x*43,y-5,281)
    rail(-16,16,y,290,24,12,"darkwood")
    for x in (-10,10):
        rail(x-1.8,x+1.8,y,290,25,13.3,"iron")
export("BentJoint")

# Cover the actual butt joint with a narrow stagger of overlapping slates on each roof pitch.
for sign in (-1,1):
    for i in range(19):
        t0=i*421/19
        t1=min(429,(i+1)*421/19+3.3)
        z0=roof_top(sign*t0)+.4
        z1=roof_top(sign*t1)+.4
        x=(-1 if i%2 else 1)*1.4
        prism((x,sign*t0,z0),(x,sign*t1,z1),18+rng.uniform(-1,2),3,"slate")
export("SlateSeam")

# Independently bedded pier shoes and continuous top plate close small variations in the scans.
for y in (-399,399):
    post(0,y,-2,12,37,39,"stone")
    post(0,y,11,16,32,34,"stone")
    sign=1 if y>0 else -1
    post(0,y+sign*11,12,292,35,9,"oak")
    for z in (52,174,265):
        pin(0,y+sign*16,z)
export("PierShoes")
for y in (-399,399):
    rail(-220,220,y,291,20,15,"oak")
rail(-220,220,0,510,16,19,"darkwood")
export("LongPlates")

# Central gate posts carry the forged pintles, straps and a chamfered stone curb at the root.
post(0,0,-3,15,31,32,"stone")
post(0,0,12,169,20,22,"oak")
post(0,0,168,172,21,23,"darkwood")
for z in (26,103):
    post(0,0,z-3,z+3,21.5,23.4,"iron")
    prism((-8,-12,z),(8,-12,z),2.2,2.2,"iron",sides=6)
export("GatePier")

for z in (27,103):
    prism((-13,-2,z),(0,0,z),3.8,3.8,"iron",sides=8)
    prism((0,0,z-1),(0,0,z+6),2.1,2.1,"iron",sides=10)
    prism((-12,-5,z),(-12,2,z),5.5,5.5,"iron",sides=8)
export("HingePintles")

for z in (24,65,106):
    rail(-120,120,0,z,7,13,"oak")
export("FenceRails")

# Feed crib. Tilted front slats leave hay accessible above a boarded trough.
for x in (-59,59):
    prism((x,-16,0),(x,-16,77),7,7,"oak")
    prism((x,14,0),(x,14,93),7,7,"oak")
    prism((x,-16,53),(x,-34,99),6,6,"oak")
for y,z in ((-15,42),(-15,56),(15,42),(15,56),(15,90),(-34,99)):
    rail(-62,62,y,z,5,11 if z<60 else 6,"lightwood")
for x in range(-48,49,12):
    prism((x,-17,57),(x,-34,98),3.5,4.5,"oak")
for x in range(-53,54,15):
    prism((x,-15,39),(x,15,39),14.5,4,"darkwood")
export("HayCrib")

# A flush line of drainage flags behind the stalls; slight gaps and irregular sizes break repetition.
for y in (-13.7,13.7):
    x=-220
    while x<219.99:
        length=min(220-x,rng.uniform(38,71))
        rail(x+.36,x+length-.36,y,0,26.4,rng.uniform(3.2,4.3),"stone")
        x+=length
export("AisleFlags")

# Single continuous packed-clay floor under all five bays. UVs are measured in metres.
slots.append("clay")
nx,ny=45,17
for j in range(ny):
    for i in range(nx):
        x=-1107+i*2214/(nx-1)
        y=-396+j*792/(ny-1)
        height=.48+.12*math.sin(x*.028+y*.024)+rng.uniform(-.08,.08)
        vertices.append((x,-y,height))
for j in range(ny-1):
    for i in range(nx-1):
        a=j*nx+i
        corners=(a,a+nx,a+nx+1,a+1)
        faces.append(corners)
        surfaces.append(0)
        uvs.extend([(vertices[v][0]/180,-vertices[v][1]/180) for v in corners])
export("PackedFloor")

# Quiet dark water recessed inside the stone lip. A rounded capsule follows the bowl.
prism((-52,0,0),(52,0,0),45,.8,"water",sides=12)
for sign in (-1,1):
    for i in range(7):
        t=(i+.5)/7
        w=45*math.sqrt(1-t*t)
        a=sign*(52+i*3.7); b=sign*(52+(i+1)*3.7)
        rail(min(a,b),max(a,b),0,-.05,w,.65,"water")
export("TroughWater")
