"""Set the Fab torch origin on the wooden grip, retaining its real proportions and three UV sets."""
import json
import os
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector

root=Path(os.environ["FPS_PROJECT_ROOT"])
source=root/"SourceAssets/WoodenTorch20261122/FabHandheldR2"
out=source/"Export"
bpy.ops.wm.read_factory_settings(use_empty=True)
def load_fbx(path):
    bpy.ops.import_scene.fbx(filepath=str(path))
    objects=[o for o in bpy.context.selected_objects if o.type=="MESH"]
    for o in objects:
        o.data.transform(o.matrix_world)
        o.matrix_world=Matrix.Identity(4)
        o.data.update()
    return objects

def section(mesh,z):
    points=np.asarray([v.co[:] for v in mesh.vertices])
    edges=np.asarray([edge.vertices[:] for edge in mesh.edges])
    a,b=points[edges[:,0]],points[edges[:,1]]
    crosses=(a[:,2]>z)!=(b[:,2]>z)
    a,b=a[crosses],b[crosses]
    xy=a[:,:2]+(b[:,:2]-a[:,:2])*((z-a[:,2])/(b[:,2]-a[:,2]))[:,None]
    return xy

# The original held mesh is normalized to this same hand coordinate system.
def grip_profile(mesh):
    result=[]
    for z in np.linspace(-.056,.056,29):
        pts=section(mesh,z)*100.
        pts[:,1]*=-1 # UE FBX (X, -Y, Z)
        result.append([round(z*100.,4),pts.round(5).tolist()])
    return result

old=load_fbx(root/"SourceAssets/Kukri20261020/Export/SM_Kukri.fbx")[0]
old_profile=grip_profile(old.data)
bpy.data.objects.remove(old,do_unlink=True)
bpy.data.orphans_purge(do_recursive=True)
parts=load_fbx(source/"Original/torch.fbx")
by_slot={o.data.materials[0].name:o for o in parts}
wood,cloth=by_slot["Wood"].data,by_slot["Cloth"].data
bottom=min(v.co.z for v in wood.vertices)
cloth_z=[v.co.z for v in cloth.vertices]
top=max(cloth_z)
z=bottom+.56*(min(cloth_z)-bottom)
cut=section(wood,z)
center=(cut.min(axis=0)+cut.max(axis=0))*.5
origin=Vector((*center,z))
for obj in parts:
    obj.data.transform(Matrix.Translation(-origin)); obj.data.update()
head_z=top-z-.012
head=section(cloth,head_z)
head_center=(head.min(axis=0)+head.max(axis=0))*.5
socket=[float(head_center[0]*100),float(-head_center[1]*100),float(head_z*100)]
fit=dict(grip_from_butt_cm=(z-bottom)*100,length_cm=(top-bottom)*100,
         grip_width_depth_cm=((cut.max(axis=0)-cut.min(axis=0))*100).tolist(),
         flame_socket_ue_cm=socket,old_profile_cm=old_profile,new_profile_cm=grip_profile(wood))
(out/"fit.json").write_text(json.dumps(fit),encoding="utf8")

def make_material(part):
    mat=by_slot[part].data.materials[0]
    mat.use_nodes=True
    nodes=mat.node_tree.nodes; links=mat.node_tree.links
    nodes.clear()
    shader=nodes.new("ShaderNodeBsdfPrincipled")
    target=nodes.new("ShaderNodeOutputMaterial")
    links.new(shader.outputs["BSDF"],target.inputs["Surface"])
    def sample(role,colorspace):
        node=nodes.new("ShaderNodeTexImage")
        img=bpy.data.images.load(str(out/f"T_HandheldTorch_{part}_{role}.png"))
        img.colorspace_settings.name=colorspace
        img.pack()
        node.image=img
        return node.outputs["Color"]
    links.new(sample("BaseColor","sRGB"),shader.inputs["Base Color"])
    orm=nodes.new("ShaderNodeSeparateColor")
    links.new(sample("ORM","Non-Color"),orm.inputs["Color"])
    links.new(orm.outputs["Green"],shader.inputs["Roughness"])
    links.new(orm.outputs["Blue"],shader.inputs["Metallic"])
    # The painter UE export uses DirectX tangent normals; Blender uses OpenGL (+Y).
    curve=nodes.new("ShaderNodeRGBCurve")
    curve.mapping.curves[1].points[0].location=(0,1)
    curve.mapping.curves[1].points[-1].location=(1,0)
    curve.mapping.update()
    links.new(sample("Normal","Non-Color"),curve.inputs["Color"])
    norm=nodes.new("ShaderNodeNormalMap")
    links.new(curve.outputs["Color"],norm.inputs["Color"])
    links.new(norm.outputs["Normal"],shader.inputs["Normal"])
    if part=="Cloth":
        links.new(sample("Opacity","Non-Color"),shader.inputs["Alpha"])
for part in ("Wood","Cloth","Rope"): make_material(part)
bpy.ops.object.select_all(action="DESELECT")
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=by_slot["Wood"]
bpy.ops.object.join()
torch=bpy.context.object
torch.name=torch.data.name="SM_WoodenTorch"
bpy.ops.export_scene.fbx(filepath=str(out/"SM_WoodenTorch.fbx"),use_selection=True,object_types={"MESH"},
    apply_unit_scale=True,bake_anim=False,axis_forward="-Y",axis_up="Z",mesh_smooth_type="FACE",use_triangles=True,path_mode="STRIP")
# Embed the authored maps in the editable assembly so it can be opened from the recovery copy.
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=str(source/"HandheldTorch_Fit.blend"))
scene=bpy.context.scene
scene.render.engine="CYCLES";scene.cycles.samples=12
scene.render.film_transparent=True
scene.render.resolution_x,scene.render.resolution_y=256,768
scene.render.resolution_percentage=100
mid=Vector((0.,0.,(top+bottom)*.5-z))
bpy.ops.object.camera_add(location=mid+Vector((.55,-1.65,.09)))
cam=bpy.context.object
cam.rotation_euler=(mid-cam.location).to_track_quat("-Z","Y").to_euler()
cam.data.type="ORTHO";cam.data.ortho_scale=(top-bottom)*1.1;scene.camera=cam
for loc,power,size in [((-.45,-.55,.65),42,.6),((.4,-.35,.28),28,.55),((.15,.43,.6),40,.46)]:
    bpy.ops.object.light_add(type="AREA",location=loc)
    lamp=bpy.context.object
    lamp.rotation_euler=(mid-lamp.location).to_track_quat("-Z","Y").to_euler()
    lamp.data.energy,lamp.data.shape,lamp.data.size=power,"DISK",size
scene.render.filepath=str(out/"ue_wooden_torch.png")
bpy.ops.render.render(write_still=True)
