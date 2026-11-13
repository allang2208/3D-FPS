"""Build the playable grip and its workbench pictogram from the two production meshes."""
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

here = Path(__file__).resolve().parent
library = here.parents[1]
name = "SM_Zhanmadao_Grip_Pojun"
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

def load_parts(path, names):
    with bpy.data.libraries.load(str(path), link=False) as (_, target):
        target.objects = names
    for obj in target.objects:
        scene.collection.objects.link(obj)
    return target.objects

shaft, wrap = load_parts(library / "SteelWarhammer20261014/ModulesV1/Warhammer_Modular_Editable.blend",
                         ["SM_Warhammer_shaft_factory", "SM_Warhammer_grip_factory"])
factory, = load_parts(here.parent / "Zhanmadao_Modular_Editable.blend", ["SM_Zhanmadao_Grip_V1"])
# In the authored hammer frame the top of the dao grip sits at Z=.84.
# Keep the entire contact surface, with its unscaled UVs and baked grip diameter.
for obj in (shaft, wrap):
    obj.location.z -= .84

def native_collar(label, plane, upper, shift):
    mesh = factory.data.copy()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    cut = bmesh.ops.bisect_plane(bm, geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                                 plane_co=(0,0,plane), plane_no=(0,0,1),
                                 clear_inner=upper, clear_outer=not upper)
    rim = [e for e in cut["geom_cut"] if isinstance(e,bmesh.types.BMEdge) and e.is_boundary]
    if not rim:
        raise RuntimeError("Missing dao collar contour: " + label)
    caps=bmesh.ops.holes_fill(bm, edges=rim, sides=0)["faces"]
    bmesh.ops.triangulate(bm, faces=caps)
    bm.to_mesh(mesh)
    bm.free()
    collar = bpy.data.objects.new(label, mesh)
    scene.collection.objects.link(collar)
    collar.location.z = shift
    return collar

native_length = .33349986556587735
length = .945
upper = native_collar("DaoUpper", -.012, True, 0)
lower = native_collar("DaoLower", -native_length+.012, False, native_length-length)
bpy.data.objects.remove(factory, do_unlink=True)

def coupling(label, a, b, za, zb):
    # Match each end's cross section independently, including off-axis contours.
    def outline(obj, plane):
        vs = [v.co + obj.location for v in obj.data.vertices if abs(v.co.z+obj.location.z-plane)<.00002]
        if not vs:
            raise RuntimeError("Missing assembly rim on " + obj.name)
        vs.sort(key=lambda v: math.atan2(v.y,v.x))
        return [max(vs,key=lambda v: v.x*math.cos(t)+v.y*math.sin(t)) for t in angles]
    angles = [math.tau*i/96 for i in range(96)]
    first,last = outline(a,za),outline(b,zb)
    verts,faces = [],[]
    for t,gain in [(0,1),(.16,1.045),(.28,1.065),(.72,1.065),(.84,1.045),(1,1)]:
        for v,w in zip(first,last):
            co=v.lerp(w,t)
            verts.append((co.x*gain,co.y*gain,za+(zb-za)*t))
    for row in range(5):
        for i in range(96):
            j=(i+1)%96
            faces.append((row*96+i,(row+1)*96+i,(row+1)*96+j,row*96+j))
    mesh=bpy.data.meshes.new(label)
    mesh.from_pydata(verts,[],faces)
    mesh.materials.append(bpy.data.materials.get("M_SharedGrip_Steel") or bpy.data.materials.new("M_SharedGrip_Steel"))
    uv=mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        poly.use_smooth=True
        for loop in poly.loop_indices:
            index=mesh.loops[loop].vertex_index
            x=index%96
            uv.data[loop].uv=((96 if x==0 and poly.index%96==95 else x)/96,(index//96)/5)
    obj=bpy.data.objects.new(label,mesh)
    scene.collection.objects.link(obj)
    return obj

top_band=coupling("UpperBand",upper,shaft,-.012,-.020)
foot_band=coupling("FootBand",wrap,lower,-.925,-length+.012)
bpy.ops.object.select_all(action="DESELECT")
for obj in (shaft,wrap,upper,lower,top_band,foot_band):
    obj.hide_set(False)
    obj.select_set(True)
bpy.context.view_layer.objects.active=upper
bpy.ops.object.join()
grip=bpy.context.object
grip.name=grip.data.name=name
print("Pojun material slots:", [m.name for m in grip.data.materials], flush=True)
bpy.ops.export_scene.fbx(filepath=str(here/(name+".fbx")),use_selection=True,object_types={"MESH"},
                         axis_forward="-Y",axis_up="Z",bake_anim=False,mesh_smooth_type="FACE",use_tspace=True,path_mode="STRIP")
# Orthographic part portrait for the actual workbench option.
cam=bpy.data.cameras.new("IconCamera")
camera=bpy.data.objects.new("IconCamera",cam)
scene.collection.objects.link(camera)
target=Vector((0,0,-length*.5))
camera.location=target+Vector((.15,-2,.18))
camera.rotation_euler=((target-camera.location).to_track_quat("-Z","Y").to_matrix() @ Matrix.Rotation(math.radians(43),3,"Z")).to_euler()
cam.type="ORTHO"
cam.ortho_scale=.84
scene.camera=camera
scene.render.engine="CYCLES"
scene.cycles.samples=12
scene.render.film_transparent=True
for loc,power,size in [((1,-2,1),160,1.2),((-1,-.5,0),60,.9),((0,1,0),100,.8)]:
    light=bpy.data.lights.new("IconSoftbox","AREA")
    light.energy=power
    light.shape="DISK"
    light.size=size
    obj=bpy.data.objects.new("IconSoftbox",light)
    scene.collection.objects.link(obj)
    obj.location=loc
    obj.rotation_euler=(target-obj.location).to_track_quat("-Z","Y").to_euler()
scene.render.resolution_x=scene.render.resolution_y=768
scene.render.resolution_percentage=100
scene.render.image_settings.color_mode="RGBA"
scene.render.filepath=str(here/"GripIcon.png")
bpy.ops.render.render(write_still=True)
