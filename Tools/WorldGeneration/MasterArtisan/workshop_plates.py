"""Author the workshop's selection plates from the gameplay preview meshes at a matching camera angle."""
import os
from pathlib import Path
import bpy
from mathutils import Vector

source=Path(os.environ["VILLAGE_SIEGE_SOURCE"])
output=Path(os.environ["VILLAGE_SIEGE_PLATES"])
output.mkdir(parents=True,exist_ok=True)
for model in ("Trebuchet","Ballista"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    bpy.ops.import_scene.fbx(filepath=str(source/f"SM_{model}Preview.fbx"))
    parts=[ob for ob in scene.objects if ob.type=="MESH"]
    for mat in {m for ob in parts for m in ob.data.materials if m}:
        mat.use_nodes=True
        nodes=mat.node_tree.nodes
        bsdf=nodes.get("Principled BSDF")
        if "Ballista" in mat.name:
            t=nodes.new("ShaderNodeTexImage")
            t.image=bpy.data.images.load(str(source/"T_BallistaBase.png"))
            mat.node_tree.links.new(t.outputs["Color"],bsdf.inputs["Base Color"])
        else:
            colors={"Oak":(.27,.127,.050),"Iron":(.17,.18,.19),"Stone":(.34,.32,.29),"Leather":(.12,.055,.024)}
            bsdf.inputs["Base Color"].default_value=(*colors.get(mat.name.split(".")[0],(.22,.16,.09)),1.)
            bsdf.inputs["Metallic"].default_value=.7 if "Iron" in mat.name else 0.
    corners=[ob.matrix_world@Vector(c) for ob in parts for c in ob.bound_box]
    lo=Vector([min(v[i] for v in corners) for i in range(3)])
    hi=Vector([max(v[i] for v in corners) for i in range(3)])
    center=(lo+hi)/2
    size=max(hi-lo)
    bpy.ops.mesh.primitive_plane_add(size=20*size,location=(center.x,center.y,lo.z-.004*size))
    floor=bpy.data.materials.new("workshop backdrop")
    floor.use_nodes=True
    ground=floor.node_tree.nodes.get("Principled BSDF")
    ground.inputs["Base Color"].default_value=(.030,.035,.038,1.)
    ground.inputs["Roughness"].default_value=.82
    bpy.context.object.data.materials.append(floor)
    camera=bpy.data.cameras.new("Plate");ob=bpy.data.objects.new("Plate",camera);scene.collection.objects.link(ob)
    direction=Vector((.48,-1.,.45)).normalized()
    ob.location=center+direction*size*3
    ob.rotation_euler=(-direction).to_track_quat("-Z","Y").to_euler()
    camera.type="ORTHO";camera.clip_end=size*25; camera.clip_start=size*.005
    scene.camera=ob
    scene.render.resolution_x=672;scene.render.resolution_y=322;scene.render.resolution_percentage=100
    bpy.context.view_layer.update()
    # Frame actual vertices, not the empty corners of the tall trebuchet's bounding box.
    proj=ob.matrix_world.inverted()
    xy=[proj@(part.matrix_world@v.co) for part in parts for v in part.data.vertices]
    xs=[q.x for q in xy];ys=[q.y for q in xy]
    camera.ortho_scale=max(max(xs)-min(xs),(max(ys)-min(ys))*672/322)*1.22
    ob.location+=ob.rotation_euler.to_quaternion() @ Vector(((max(xs)+min(xs))/2,(max(ys)+min(ys))/2,0))
    scene.world=bpy.data.worlds.new("Studio");scene.world.color=(.12,.13,.14)
    for direction,power,color in [((-.5,-1,1.4),60,(1,.86,.68)),((.5,1,.9),72,(.75,.84,1))]:
        light=bpy.data.lights.new("Softbox","AREA")
        lamp=bpy.data.objects.new("Softbox",light);scene.collection.objects.link(lamp)
        vec=Vector(direction)
        lamp.location=center+vec*size;lamp.rotation_euler=(-vec).to_track_quat("-Z","Y").to_euler()
        light.energy=power*size**2;light.shape="DISK";light.size=size;light.color=color
    scene.render.engine="CYCLES";scene.cycles.samples=12;scene.cycles.use_denoising=True
    scene.render.image_settings.file_format="JPEG";scene.render.image_settings.quality=91
    scene.render.filepath=str(output/(model+".jpg"))
    bpy.ops.render.render(write_still=True)
