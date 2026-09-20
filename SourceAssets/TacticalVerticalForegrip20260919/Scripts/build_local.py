"""Author the local hard-surface grip from the reference; no render or runtime test."""
import bpy
import bmesh
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Source"
SOURCE.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
parts = []
PARAMETERS = {
    "height_m": 0.1035, "saddle_length_m": 0.053, "saddle_width_m": 0.029,
    "body_ring_segments": 128, "body_height_segments": 400,
    "rib_count": 20, "rib_first_z": -0.046, "rib_last_z": -0.091,
    "rib_relief_m": 0.00048, "side_recess_depth_m": 0.00038,
    "notes": "Visual game-prop proportions inferred from reference, not manufacturing dimensions."
}
def material(name, dark, light, metal, rough):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*light, 1)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bs = nodes.get("Principled BSDF")
    bs.inputs["Metallic"].default_value = metal
    bs.inputs["Roughness"].default_value = rough
    coord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 6200 if metal < .5 else 1700
    noise.inputs["Detail"].default_value = 2
    noise.inputs["Roughness"].default_value = .72
    links.new(coord.outputs["Object"], noise.inputs["Vector"])
    color = nodes.new("ShaderNodeValToRGB")
    color.color_ramp.elements[0].position = .19
    color.color_ramp.elements[0].color = (*dark, 1)
    color.color_ramp.elements[1].position = .82
    color.color_ramp.elements[1].color = (*light, 1)
    links.new(noise.outputs["Fac"], color.inputs["Fac"])
    links.new(color.outputs["Color"], bs.inputs["Base Color"])
    rough_map = nodes.new("ShaderNodeMapRange")
    rough_map.inputs["From Min"].default_value = 0
    rough_map.inputs["From Max"].default_value = 1
    rough_map.inputs["To Min"].default_value = rough - .07
    rough_map.inputs["To Max"].default_value = rough + .07
    links.new(noise.outputs["Fac"], rough_map.inputs["Value"])
    links.new(rough_map.outputs["Result"], bs.inputs["Roughness"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = .28 if metal < .5 else .12
    bump.inputs["Distance"].default_value = .000033 if metal < .5 else .000008
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bs.inputs["Normal"])
    mat["author_metallic"] = metal
    return mat

poly = material("Polymer_Charcoal", (.011,.013,.016), (.032,.037,.043), 0, .73)
panel = material("Polymer_Recess", (.009,.011,.014), (.026,.030,.036), 0, .79)
metal = material("Fastener_DarkMetal", (.018,.021,.026), (.047,.053,.062), .85, .43)
cavity = material("Fastener_Inset", (.004,.005,.007), (.012,.014,.018), .6, .56)
all_materials = [poly, panel, metal, cavity]
def smoothstep(a,b,x):
    t = min(1,max(0,(x-a)/(b-a)))
    return t*t*(3-2*t)
# A continuous neck/body profile, in meters and in the UE attachment orientation.
profile = [
    (-.1035,.0171,.0095),(-.1028,.0184,.0106),(-.1015,.0195,.0116),
    (-.0980,.0199,.0119),(-.0890,.0197,.0119),(-.0710,.0192,.0117),
    (-.0520,.0187,.0115),(-.0400,.0180,.0109),(-.0300,.0164,.0100),
    (-.0260,.0163,.0099),(-.0210,.0180,.0104),(-.0160,.0215,.0118),
    (-.0120,.0248,.0132),(-.0090,.0257,.0137),(-.0062,.0255,.0135),
]
def section(z):
    for p,q in zip(profile,profile[1:]):
        if z <= q[0]:
            t=smoothstep(p[0],q[0],z)
            return p[1]*(1-t)+q[1]*t,p[2]*(1-t)+q[2]*t
    return profile[-1][1],profile[-1][2]
def panel_distance(x,z):
    radius=.0030
    qx=abs(x)-(.0124-radius)
    qz=abs(z+.067)-(.0310-radius)
    return math.hypot(max(qx,0),max(qz,0))+min(max(qx,qz),0)-radius

n=PARAMETERS["body_ring_segments"]
nz=PARAMETERS["body_height_segments"]
verts=[]
faces=[]
face_materials=[]
pitch=(PARAMETERS["rib_first_z"]-PARAMETERS["rib_last_z"])/(PARAMETERS["rib_count"]-1)
for row in range(nz+1):
    z=profile[0][0]+(profile[-1][0]-profile[0][0])*row/nz
    a,b=section(z)
    for col in range(n):
        t=2*math.pi*col/n
        cs,sn=math.cos(t),math.sin(t)
        x=a*math.copysign(abs(cs)**(2/4.5),cs)
        y=b*math.copysign(abs(sn)**(2/4.5),sn)
        d=panel_distance(x,z)
        side=smoothstep(.78,.99,abs(y)/b)
        inset=(1-smoothstep(-.0007,.0002,d))*PARAMETERS["side_recess_depth_m"]
        lip=.000065*math.exp(-(d/.00025)**2)
        y-=math.copysign(side*(inset-lip),y)
        k=round((PARAMETERS["rib_first_z"]-z)/pitch)
        if 0<=k<PARAMETERS["rib_count"]:
            center=PARAMETERS["rib_first_z"]-k*pitch
            rounded=math.exp(-((z-center)/.00068)**4)
            front=smoothstep(.72,.98,x/a)
            ends=1-smoothstep(.65,.96,abs(y)/b)
            x+=PARAMETERS["rib_relief_m"]*rounded*front*ends
        cap_groove=1-.009*math.exp(-((z+.1009)/.00019)**2)
        verts.append((x*cap_groove,y*cap_groove,z))
for row in range(nz):
    for col in range(n):
        nex=(col+1)%n
        face=(row*n+col,row*n+nex,(row+1)*n+nex,(row+1)*n+col)
        faces.append(face)
        x,y,z=[sum(verts[i][axis] for i in face)/4 for axis in range(3)]
        _,b=section(z)
        face_materials.append(1 if panel_distance(x,z)<-.0003 and abs(y)>.85*b else 0)
faces.extend([tuple(reversed(range(n))),tuple(nz*n+i for i in range(n))])
face_materials.extend([0,0])
mesh=bpy.data.meshes.new("ContinuousBody_Ribs_Recess")
mesh.from_pydata(verts,[],faces)
mesh.update()
body=bpy.data.objects.new("Grip_ContinuousBody",mesh)
scene.collection.objects.link(body)
for mat in all_materials:
    mesh.materials.append(mat)
for f,mat_index in zip(mesh.polygons,face_materials):
    f.material_index=mat_index
    f.use_smooth=len(f.vertices)==4
bm=bmesh.new()
bm.from_mesh(mesh)
bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
bm.to_mesh(mesh)
bm.free()
parts.append(body)

def finish(obj,name,mat,bevel=0):
    obj.name=name
    obj.data.materials.append(mat)
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        m=obj.modifiers.new("Soft manufactured edges","BEVEL")
        m.width=bevel
        m.segments=3
        bpy.ops.object.modifier_apply(modifier=m.name)
    for poly_face in obj.data.polygons:
        poly_face.use_smooth=True
    mod=obj.modifiers.new("Corner normals","WEIGHTED_NORMAL")
    mod.keep_sharp=True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    parts.append(obj)
    return obj
def box(name,loc,size,mat,bevel):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    obj=bpy.context.object
    obj.scale=size
    return finish(obj,name,mat,bevel)

# Cosmetic saddle and fastener shapes for a game asset; no physical mounting specification.
box("SaddleFloor",(0,0,-.0060),(.052,.026,.0030),poly,.0008)
for sign in [-1,1]:
    box("SaddleRaisedLip_"+str(sign),(0,sign*.0111,-.0032),(.053,.0068,.0064),poly,.0009)
    for index,x in enumerate([-.0088,.0088]):
        z=-.0111
        y=sign*.0139
        bpy.ops.mesh.primitive_torus_add(major_segments=48,minor_segments=12,
            location=(x,y,z),rotation=(math.pi/2,0,0),
            major_radius=.0021,minor_radius=.00062)
        finish(bpy.context.object,"FastenerRing_%s_%s"%(sign,index),metal)
        bpy.ops.mesh.primitive_cylinder_add(vertices=6,radius=.00148,depth=.00020,
            location=(x,sign*.01384,z),rotation=(math.pi/2,0,0))
        finish(bpy.context.object,"FastenerHexInset_%s_%s"%(sign,index),cavity,.00008)
# Retain separately editable parts in the author source.
for obj in parts:
    obj["asset_role"]="reference-authored candidate component"
scene["reference_source"]="Reference/user_reference.png and three_views.png"
scene["model_route"]="User selected local Blender/Vibe3D on 2026-09-19"
scene["parameters_json"]=json.dumps(PARAMETERS)
bpy.ops.object.select_all(action="DESELECT")
for obj in parts:
    obj.select_set(True)
bpy.context.view_layer.objects.active=body
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/"TacticalVerticalForegrip_Construction.blend"))
(ROOT/"local_authoring_parameters.json").write_text(json.dumps(PARAMETERS,indent=2),encoding="utf-8")
print("LOCAL_CONSTRUCTION_SAVED "+str(SOURCE/"TacticalVerticalForegrip_Construction.blend"),flush=True)
