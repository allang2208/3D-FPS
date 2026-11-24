"""Build the attached linen lean-to and its fixed furnishings. Author coordinates are UE metres."""
from pathlib import Path
import json
import math
import sys
import bpy
from mathutils import Matrix, Vector

out = Path(__file__).resolve().parent
sys.path.insert(0, str(out))
from yard_furnishings import dress
from yard_workfloor import dress_floor
from yard_wear_uv import apply as apply_wear_uv
from yard_sites import WEST, HALF, wall as ledger

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
mats = {n: bpy.data.materials.new(n) for n in ("Canvas","Oak","Stone","Iron","Bark","End","Split","Clinker","Coal","Brick")}
parts, solids = [], []

def vec(p):
    return Vector((p[0], -p[1], p[2]))

def active(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

def surface_uv(obj, material):
    layer = obj.data.uv_layers.active or obj.data.uv_layers.new(name="Surface")
    offset = .17 * (len(parts) % 11)
    span = obj.dimensions
    longest = max(range(3),key=lambda i:span[i])
    for face in obj.data.polygons:
        normal = max(range(3), key=lambda i:abs(face.normal[i]))
        axes = [i for i in range(3) if i!=normal]
        if material in ("Oak","Split") and longest in axes:
            axes = [next(i for i in axes if i!=longest),longest]
        for li in face.loop_indices:
            v = obj.data.vertices[obj.data.loops[li].vertex_index].co
            layer.data[li].uv = (v[axes[0]]+.31+offset, v[axes[1]]*.68+.54+offset)

def box(name, pos, size, mat, yaw=0., bevel=.009):
    bpy.ops.mesh.primitive_cube_add(size=1,location=vec(pos))
    obj=bpy.context.object
    obj.name=name
    obj.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj.data.materials.append(mats[mat])
    if bevel:
        mod=obj.modifiers.new("Worn arris","BEVEL")
        mod.width=bevel
        mod.segments=2
        bpy.ops.object.modifier_apply(modifier=mod.name)
    surface_uv(obj,mat)
    obj.rotation_euler.z=-math.radians(yaw)
    parts.append(obj)
    return obj

def beam(name,a,b,w,h,mat="Oak"):
    start,end=vec(a),vec(b)
    mid=(start+end)*.5
    obj=box(name,(mid.x,-mid.y,mid.z),(w,h,(end-start).length),mat,bevel=min(w,h)*.055)
    obj.rotation_euler=(end-start).to_track_quat('Z','Y').to_euler()
    return obj

def poly(name,vertices,faces,materials,indices,uvs=None):
    data=bpy.data.meshes.new(name)
    # Reflection from Unreal Y to Blender Y reverses the winding.
    data.from_pydata([vec(p) for p in vertices],[],[tuple(reversed(f)) for f in faces])
    data.update()
    obj=bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(obj)
    for mat in materials:
        data.materials.append(mats[mat])
    surface_uv(obj,materials[0])
    layer=data.uv_layers.active
    for face,idx in zip(data.polygons,indices):
        face.material_index=idx
        if uvs:
            for li,uv in zip(face.loop_indices,reversed(uvs[face.index])):
                layer.data[li].uv=uv
    parts.append(obj)
    return obj

def solid(center,size,yaw=0.,pitch=0.):
    solids.append(dict(center=[100*x for x in center],size=[100*x for x in size],yaw=yaw,pitch=pitch))

west, half, slope = WEST, HALF, .075

def rail(x):
    return 3.47 + slope*x

# Outer and intermediate supports stay on the side edges of the work route.
for x in (-1.58,3.15):
    for y in (-3.48,3.48):
        top=rail(x)
        box("Stone footing",(x,y,.012),(.41,.41,.28),"Stone",bevel=.035)
        beam("Oak upright",(x,y,.12),(x,y,top),.175,.175)
        solid((x,y,top/2),(.18,.18,top))
        solid((x,y,.045),(.41,.41,.25))
        box("Foot strap",(x,y,.30),(.19,.19,.07),"Iron")
        beam("Knee down the eave",(x,y,top-.62),(x,y-math.copysign(.62,y),top-.07),.085,.11)
        beam("Knee under the rafter",(x,y,top-.62),(x+.62,y,rail(x+.62)-.06),.095,.11)
    beam("Longitudinal bearer",(x,-3.57,rail(x)),(x,3.57,rail(x)),.16,.20)

beam("Wall ledger",(ledger(-half),-half,rail(ledger(-half))),(ledger(half),half,rail(ledger(half))),.20,.24)
rafters=(-3.48,-1.74,0.,1.74,3.48)
for y in rafters:
    right=ledger(y)
    beam("Spanning rafter",(west,y,rail(west)+.09),(right+.055,y,rail(right)+.09),.115,.15)
    box("Ledger bracket",(right-.08,y,rail(right)-.05),(.22,.07,.36),"Iron",bevel=.005)
for y in (-half,half):
    beam("Fascia batten",(west,y,rail(west)+.11),(ledger(y),y,rail(ledger(y))+.11),.06,.08)

def cloth_z(x,y):
    sag=math.sin(math.pi*(y+3.48)/1.74)**2
    return rail(x)+.18-.097*sag+.009*sag*math.sin(8*x+2*y)
verts,faces,uv=[],[],[]
nx,ny=52,64
for j in range(ny+1):
    y=-half+2*half*j/ny
    for i in range(nx+1):
        x=west+(ledger(y)+.12-west)*i/nx
        verts.append((x,y,cloth_z(x,y)))
        uv.append((x*.76,y*.76))
for j in range(ny):
    for i in range(nx):
        k=j*(nx+1)+i
        faces.append((k,k+1,k+nx+2,k+nx+1))
cloth=poly("Rain canvas",verts,faces,["Canvas"],[0]*len(faces),[[uv[k] for k in f] for f in faces])
active(cloth)
for face in cloth.data.polygons:
    face.use_smooth=True
mod=cloth.modifiers.new("Folded canvas","SOLIDIFY")
mod.thickness=.016
bpy.ops.object.modifier_apply(modifier=mod.name)
# Raised lap seams run with the drainage. The high edge is held by a continuous counterflashing.
for y in (-2.60,-.87,.87,2.60):
    end=ledger(y)+.08
    beam("Lapped linen seam",(west+.03,y,cloth_z(west+.03,y)+.004),(end,y,cloth_z(end,y)+.004),.028,.013,"Canvas")
beam("Folded wall flashing",(ledger(-half),-half,rail(ledger(-half))+.19),(ledger(half),half,rail(ledger(half))+.19),.23,.075,"Iron")
# Narrow strips follow the slight skew of the facade without collision extending through the wall.
for a,b in zip([-half,-1.89,0.,1.89],[-1.89,0.,1.89,half]):
    y=(a+b)/2
    end=ledger(y)+.08
    x=(west+end)*.5
    solid((x,y,rail(x)+.135),((end-west)*math.hypot(1,slope),b-a,.105),pitch=math.degrees(math.atan(slope)))

# Three overlapping repairs follow the sag of the panel, with folded corners and hand stitches.
for cx,cy,w,h in [(-.72,2.14,.62,.43),(4.40,-2.16,.84,.47),(6.14,1.12,.43,.31)]:
    points=[]
    nu,nv=8,6
    for j in range(nv+1):
        for i in range(nu+1):
            x=cx+w*(i/nu-.5)+.030*(j/nv-.5)
            y=cy+h*(j/nv-.5)+.014*math.sin(i*.85)
            points.append((x,y,cloth_z(x,y)+.014))
    quads=[]
    for j in range(nv):
        for i in range(nu):
            k=j*(nu+1)+i
            quads.append((k,k+1,k+nu+2,k+nu+1))
    poly("Darned canvas patch",points,quads,["Canvas"],[0]*len(quads),
         [[(points[k][0]*.93+.23,points[k][1]*.93) for k in f] for f in quads])
    for j in (0,nv):
        for i in range(0,nu,2):
            a,b=points[j*(nu+1)+i],points[j*(nu+1)+i+1]
            beam("Waxed linen stitch",(a[0],a[1],a[2]+.008),(b[0],b[1],b[2]+.008),.009,.009,"Canvas")

dress(box,beam,poly,solid)
dress_floor(poly,beam)
bpy.context.view_layer.update()
apply_wear_uv(parts)

# Keep the editable boards, logs and fittings as individual named objects in the Blender source.
bpy.ops.wm.save_as_mainfile(filepath=str(out/"SmithSmeltingCanopy.blend"))
active(cloth)
for obj in parts:
    obj.select_set(True)
bpy.ops.object.join()
cloth.name="SM_SmithSmeltingCanopy"
cloth.data.transform(cloth.matrix_world)
cloth.matrix_world=Matrix.Identity(4)
bpy.ops.export_scene.fbx(filepath=str(out/"SM_SmithSmeltingCanopy.fbx"),use_selection=True,
    object_types={'MESH'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',bake_anim=False)
(out/"collision.json").write_text(json.dumps(solids,indent=2),encoding="utf-8")
