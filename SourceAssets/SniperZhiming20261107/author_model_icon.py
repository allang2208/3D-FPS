"""Round Zhiming: shared exterior mesh, M24 finish UVs, appearance plate and gunsmith icon."""
import math
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent
OUT = ROOT / "Exports"
ART = ROOT / "Concept"
KEY = "SM_SniperZhiming"
SCENE_FILE = ART / "Zhiming_Round_v06.blend"
MARK = OUT / "T_Zhiming_RoundArtwork.png"


def load_object(path, name):
    with bpy.data.libraries.load(str(path), link=False) as (_, data):
        data.objects=[name]
    obj=data.objects[0]
    bpy.context.scene.collection.objects.link(obj)
    return obj


def factory_uv_corners(native):
    mesh=native.data
    plane=sorted((p for p in mesh.polygons if p.normal.x < -.999),key=lambda p:-p.area)[:2]
    uv=mesh.uv_layers[0]
    points={tuple(mesh.vertices[mesh.loops[i].vertex_index].co):uv.data[i].uv.copy()
            for p in plane for i in p.loop_indices}
    corners=sorted(points, key=lambda xyz: (round(xyz[1],5),xyz[2]))
    return [points[c] for c in corners]


def shader(name):
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    tree=m.node_tree
    return m,tree.nodes,tree.links.new,tree.nodes.get("Principled BSDF")


def image_node(nodes,path,linear=False):
    n=nodes.new("ShaderNodeTexImage")
    n.image=bpy.data.images.load(str(path),check_existing=True)
    if linear:n.image.colorspace_settings.name="Non-Color"
    return n


def metal():
    m,n,link,p=shader("ZhimingGraphite")
    original=SOURCE/"M24CustomScope20261026/Original/GLTF/textures"
    regional=SOURCE/"M24Surface20261027/Textures"
    base=image_node(n,original/"sniper_baseColor.png")
    orm=image_node(n,original/"sniper_metallicRoughness.png",True)
    region=image_node(n,regional/"T_M24_Body_Regions.png",True)
    normal=image_node(n,regional/"T_M24_Body_Refined_N.png",True)
    split=n.new("ShaderNodeSeparateColor");link(orm.outputs["Color"],split.inputs[0])
    finish=n.new("ShaderNodeMixRGB")
    finish.inputs[1].default_value=(.019,.019,.018,1)
    finish.inputs[2].default_value=(.034,.036,.039,1)
    link(split.outputs["Blue"],finish.inputs[0])
    color=n.new("ShaderNodeMixRGB");color.inputs[0].default_value=.20
    link(finish.outputs[0],color.inputs[1]);link(base.outputs["Color"],color.inputs[2])
    link(color.outputs[0],p.inputs["Base Color"]);link(split.outputs["Blue"],p.inputs["Metallic"])
    channels=n.new("ShaderNodeSeparateColor");link(region.outputs["Color"],channels.inputs[0])
    rough=n.new("ShaderNodeMixRGB")
    link(split.outputs["Blue"],rough.inputs[0])
    link(channels.outputs["Green"],rough.inputs[1]);link(channels.outputs["Red"],rough.inputs[2])
    link(rough.outputs[0],p.inputs["Roughness"])
    nm=n.new("ShaderNodeNormalMap");link(normal.outputs["Color"],nm.inputs["Color"]);link(nm.outputs[0],p.inputs["Normal"])
    return m


def ink():
    m,n,link,p=shader("Zhiming_Inlay")
    t=image_node(n,MARK)
    link(t.outputs["Color"],p.inputs["Base Color"])
    detail=image_node(n,OUT/"T_Zhiming_RoundFinish.png",True)
    detail.image.alpha_mode="CHANNEL_PACKED"
    normal=n.new("ShaderNodeNormalMap")
    link(detail.outputs["Color"],normal.inputs["Color"])
    link(normal.outputs["Normal"],p.inputs["Normal"])
    link(detail.outputs["Alpha"],p.inputs["Roughness"])
    p.inputs["Metallic"].default_value=.72
    link(t.outputs["Alpha"],p.inputs["Alpha"])
    return m


def author():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    native=load_object(SOURCE/"M24Repair20261027/M24_Repaired_Editable.blend","M24_silencer")
    a,b,c,d=factory_uv_corners(native)
    bpy.data.objects.remove(native,do_unlink=True)
    ob=load_object(SOURCE/"SniperSuppressor20261019/SniperHeavySuppressor_Editable.blend","SM_SniperHeavySuppressor")
    m=ob.data
    # Widen the exterior silhouette of the existing art mesh in its transverse axes.
    m.transform(Matrix.Diagonal(Vector((1,1.52,1.52,1))))
    shell=[f for f in m.polygons if f.material_index==0]
    painted=[f for f in shell if abs(f.normal.x)<.28]
    xs=[m.vertices[i].co.x for f in shell for i in f.vertices]
    start,end=min(xs),max(xs)
    ids=sorted({i for f in painted for i in f.vertices})
    index={old:i for i,old in enumerate(ids)}
    vertices=[]
    for i in ids:
        x,y,z=m.vertices[i].co
        vertices.append((x,y*1.004,z*1.004))
    surface=bpy.data.meshes.new("Cylindrical marking")
    surface.from_pydata(vertices,[],[[index[i] for i in f.vertices] for f in painted])
    surface.update()
    decoration=bpy.data.objects.new("Zhiming curved ink",surface)
    bpy.context.scene.collection.objects.link(decoration)
    draw_uv=surface.uv_layers.new(name="UVMap")
    for f in surface.polygons:
        f.use_smooth=True
        coords=[surface.vertices[surface.loops[i].vertex_index].co for i in f.loop_indices]
        angles=[math.atan2(v.z,v.y)/(2*math.pi)+.5 for v in coords]
        wrap=max(angles)-min(angles)>.5
        for i,v,t in zip(f.loop_indices,coords,angles):
            draw_uv.data[i].uv=(1-(v.x-start)/(end-start),t+(1 if wrap and t<.5 else 0))
    decoration.data.materials.append(ink())
    uv=m.uv_layers.active
    # Preserve each finished island's unwrap and map it strictly inside factory steel.
    recess=m.materials[3]
    recess.name="Zhiming_Recess"
    for f in m.polygons:
        if f.material_index!=3:
            values=[tuple(uv.data[i].uv) for i in f.loop_indices]
            if f.material_index==0:
                # The source shell has its wrap seam on the presentation side.
                # Align factory grain lengthwise and put its wrap underneath.
                turns=[(turn+.25)%1 for turn,axial in values]
                wrap=max(turns)-min(turns)>.5
                values=[(1-axial,t+(1 if wrap and t<.5 else 0))
                        for (_,axial),t in zip(values,turns)]
            for i,(u,v) in zip(f.loop_indices,values):
                u=.035+.93*u;v=.06+.88*v
                uv.data[i].uv=a.lerp(c,u).lerp(b.lerp(d,u),v)
    prior=[f.material_index for f in m.polygons]
    m.materials.clear();m.materials.append(metal());m.materials.append(recess)
    for f,slot in zip(m.polygons,prior): f.material_index=int(slot==3)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True);decoration.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.object.join();ob.name=KEY
    return ob


def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()


def beauty(ob):
    sc=bpy.context.scene
    center=Vector([sum((min(v.co[i] for v in ob.data.vertices),max(v.co[i] for v in ob.data.vertices)))*.5 for i in range(3)])
    size=ob.dimensions.x
    sc.world=bpy.data.worlds.new("Neutral studio");sc.world.use_nodes=True
    sc.world.node_tree.nodes["Background"].inputs[0].default_value=(.59,.63,.68,1)
    sc.world.node_tree.nodes["Background"].inputs[1].default_value=.36
    sc.render.engine="CYCLES";sc.cycles.samples=64;sc.cycles.use_denoising=True
    for pos,power,w,h,color in [
        ((.12,.23,.44),7,.48,.26,(1,.96,.91)),
        ((-.1,-.15,.25),9,.48,.09,(.83,.90,1)),
        ((.47,.09,.09),2,.19,.13,(1,.91,.79)),
        ((-.16,.35,.05),1.5,.32,.12,(.92,.95,1))]:
        bpy.ops.object.light_add(type="AREA", location=center+Vector(pos))
        lamp=bpy.context.object;lamp.data.shape="RECTANGLE";lamp.data.energy=power
        lamp.data.size=w;lamp.data.size_y=h;lamp.data.color=color;aim(lamp,center)
    bpy.ops.object.camera_add(location=center+Vector((.34,.92,.23)))
    cam=bpy.context.object;aim(cam,center);cam.data.type="ORTHO";cam.data.ortho_scale=size*1.22;cam.data.clip_start=.001;sc.camera=cam
    bottom=min(v.co.z for v in ob.data.vertices)
    bpy.ops.mesh.primitive_plane_add(size=80,location=(0,0,bottom-.00005))
    m,n,l,p=shader("Warm grey sweep");p.inputs["Base Color"].default_value=(.145,.133,.121,1);p.inputs["Roughness"].default_value=.64
    bpy.context.object.data.materials.append(m)
    sc.render.resolution_x=1920;sc.render.resolution_y=960;sc.render.resolution_percentage=100
    sc.render.image_settings.file_format="PNG";sc.render.image_settings.color_mode="RGB";sc.view_settings.view_transform="AgX"
    sc.view_settings.look="AgX - Medium High Contrast"
    sc.render.filepath=str(SCENE_FILE.with_suffix(".png"))
    bpy.data.orphans_purge(do_recursive=True)
    for img in bpy.data.images:
        if img.filepath and not img.packed_file:img.pack()
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(SCENE_FILE));bpy.ops.render.render(write_still=True)


def export_mesh(ob):
    info=json.loads((SOURCE/"SniperSuppressor20261019/authoring.json").read_text(encoding="utf-8"))
    bpy.ops.object.select_all(action="DESELECT");ob.select_set(True);bpy.context.view_layer.objects.active=ob
    ob.data.transform(Matrix.Scale(100,4));bpy.context.scene.unit_settings.scale_length=.01
    bpy.ops.export_scene.fbx(filepath=str(OUT/(KEY+".fbx")),use_selection=True,object_types={"MESH"},
        axis_forward="-Y",axis_up="Z",apply_unit_scale=True,apply_scale_options="FBX_SCALE_UNITS",
        mesh_smooth_type="FACE",use_tspace=True,use_mesh_modifiers=False,bake_anim=False,add_leaf_bones=False)
    (OUT/"mesh.json").write_text(json.dumps({"tip_cm":info["tip_cm"]}),encoding="utf-8")


def icon():
    bpy.ops.wm.open_mainfile(filepath=str(SCENE_FILE),use_scripts=False)
    scene=bpy.context.scene
    ob=bpy.data.objects[KEY]
    for other in scene.objects:
        if other.type=="MESH" and other!=ob:
            other.hide_render=True
    center=ob.matrix_world @ (sum((Vector(v) for v in ob.bound_box),Vector())/8)
    scene.camera.location=center+Vector((.34,.96,.14))
    aim(scene.camera,center)
    scene.camera.data.ortho_scale=ob.dimensions.x*1.38
    scene.render.resolution_x=scene.render.resolution_y=1254
    scene.render.film_transparent=True
    scene.render.image_settings.color_mode="RGBA"
    scene.cycles.samples=40
    # Silver values in the monochrome plate preserve the waveform against the graphite.
    layer=ob.data.materials.get("Zhiming_Inlay")
    nodes=layer.node_tree.nodes
    link=layer.node_tree.links.new
    sample=next(n for n in nodes if n.type=="TEX_IMAGE" and n.image.name==MARK.name)
    ramp=nodes.new("ShaderNodeValToRGB")
    low,high=ramp.color_ramp.elements
    low.position=.026
    low.color=(.012,.012,.012,1)
    high.position=.32
    high.color=(.78,.78,.78,1)
    surface=nodes.get("Principled BSDF")
    link(sample.outputs["Color"],ramp.inputs["Fac"])
    link(ramp.outputs["Color"],surface.inputs["Base Color"])
    surface.inputs["Metallic"].default_value=.36
    with tempfile.TemporaryDirectory(prefix="zhiming_icon_") as work:
        subject=Path(work)/"subject.png"
        scene.render.filepath=str(subject)
        bpy.ops.render.render(write_still=True)
        subprocess.run(["py","-3.11",str(ROOT/"frame_icon.py"),str(subject)],check=True)


if __name__=="__main__":
    if "--icon-only" not in sys.argv:
        obj=author()
        beauty(obj)
        if "--appearance-only" not in sys.argv:
            export_mesh(obj)
    icon()
