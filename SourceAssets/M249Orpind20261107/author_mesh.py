"""Build the viewmodel in the native PKM arm bind space, with independent editable art parts."""
from pathlib import Path
import json
import math
import re
import sys
import bpy
import numpy as np
from mathutils import Matrix,Vector

ROOT=Path(__file__).resolve().parent
EXPORT=ROOT/"Exports"
EXPORT.mkdir(exist_ok=True)
PKM=ROOT.parent/"PKMLowpoly20260922"
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(PKM/"Accessories14/PKM_Modular_Editable.blend"),use_scripts=False)
rig=bpy.data.objects["PKM_Manny_Rig"]
rig.animation_data_clear()
rig.data.pose_position="REST"
bpy.context.view_layer.update()
# Source X points back along the model. Store model/bone landmarks in UE cm, as used by motion_fit.
def mount_cm(raw):
    x,y,z=raw
    return Vector((5.45+y,x-28.6,z-5.3))
def blender_cm(v):return Vector((v[0],-v[1],v[2]))*.01
base=Matrix([[0,1,0,.0545],[-1,0,0,.286],[0,0,1,-.053],[0,0,0,1]])
bind=json.loads((PKM/"ArmHinge55/Inputs/PKM_bind.json").read_text())
rest={n:blender_cm(t[:3]) for n,t in zip(bind["names"],bind["rest"])}
feed0=blender_cm(mount_cm((1.45,-2.25,3.55)))
mirror=Matrix.Diagonal((-.72,.72,.72,1))
feedmap=Matrix.Translation(feed0)@mirror@Matrix.Translation(-rest["PKM_Belt_00"])
components=[]
def bind_rigid(o,bone):
    o.parent=rig
    o.matrix_parent_inverse=Matrix.Identity(4)
    o.matrix_world=Matrix.Identity(4)
    o.vertex_groups.clear()
    g=o.vertex_groups.new(name=bone)
    g.add(list(range(len(o.data.vertices))),1,"REPLACE")
    for mod in list(o.modifiers):o.modifiers.remove(mod)
    o.modifiers.new("Armature","ARMATURE").object=rig
    o["mechanical_bone"]=bone

def material(name):
    known=bpy.data.materials.get(name)
    if known:return known
    mat=bpy.data.materials.new(name)
    if not name.startswith("M249_"):return mat
    mat.use_nodes=True
    nodes=mat.node_tree.nodes
    link=mat.node_tree.links.new
    bsdf=next(n for n in nodes if n.type=="BSDF_PRINCIPLED")
    if name=="M249_MagnifierReticle":
        bsdf.inputs["Base Color"].default_value=(.7,.005,.002,1)
        bsdf.inputs["Emission Color"].default_value=(1,.005,.002,1)
        bsdf.inputs["Emission Strength"].default_value=3
        return mat
    if name=="M249_Riser":
        bsdf.inputs["Base Color"].default_value=(.025,.03,.035,1)
        bsdf.inputs["Metallic"].default_value=.75
        bsdf.inputs["Roughness"].default_value=.42
        return mat
    if name in ("M249_Glass","M249_HoloGlass","M249_MagnifierGlass"):
        bsdf.inputs["Base Color"].default_value=(.12,.23,.24,1)
        bsdf.inputs["Roughness"].default_value=.11
        bsdf.inputs["Transmission Weight"].default_value=.85
        bsdf.inputs["Alpha"].default_value=.18
        return mat
    def texture(file,linear=False):
        tex=nodes.new("ShaderNodeTexImage")
        tex.image=bpy.data.images.load(str(ROOT/"Textures"/file),check_existing=True)
        if linear:tex.image.colorspace_settings.name="Non-Color"
        return tex
    color=texture("T_M249_Color.png")
    link(color.outputs["Color"],bsdf.inputs["Base Color"])
    link(color.outputs["Alpha"],bsdf.inputs["Alpha"])
    orm=nodes.new("ShaderNodeSeparateColor")
    link(texture("T_M249_ORM.png",True).outputs["Color"],orm.inputs["Color"])
    link(orm.outputs["Green"],bsdf.inputs["Roughness"])
    link(orm.outputs["Blue"],bsdf.inputs["Metallic"])
    normal=nodes.new("ShaderNodeNormalMap")
    link(texture("T_M249_Normal.png",True).outputs["Color"],normal.inputs["Color"])
    link(normal.outputs["Normal"],bsdf.inputs["Normal"])
    if name not in ('M249_HoloHousing','M249_OpticalHousing'):
        link(texture("T_M249_Emission.jpeg").outputs["Color"],bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value=3
    return mat
def slot(o,name):
    o.data.materials.clear()
    o.data.materials.append(material(name))

# Carry forward only the short exposed decorative feed strip. Convert each element
# about its source centre so UVs, links and the separate travelling props survive.
for o in list(bpy.context.scene.objects):
    b=o.get("mechanical_bone","")
    m=re.fullmatch(r"(?:New_)?PKM_Belt_(Link_)?(\d+)",b)
    if not m or int(m.group(2))> (7 if m.group(1) else 8): continue
    rawmat=o.data.materials[0].name
    if "Case" in rawmat:finish="Case"
    elif "Copper" in rawmat:finish="Copper"
    else:finish="Link"
    o.data=o.data.copy()
    xf=feedmap@o.matrix_world
    o.data.transform(xf)
    if xf.to_3x3().determinant()<0:o.data.flip_normals()
    o.name="M249_"+o.name.removeprefix("PKM_")
    slot(o,"Feed"+finish+("__NewBelt" if b.startswith("New_") else "__OldBelt"))
    bind_rigid(o,b)
    components.append(o)
for o in list(bpy.context.scene.objects):
    if o!=rig and o not in components: bpy.data.objects.remove(o,do_unlink=True)

# Carry the current native V9 surface, UVs, weights and joint correctives.
# The older editable V7 file has the skin materials but lacks these morphs.
existing=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(ROOT/'Repair03/PKM_V9_Arms.fbx'))
imported=set(bpy.data.objects)-existing
skin=next(o for o in imported if o.type=='MESH')
source_rig=next(o for o in imported if o.type=='ARMATURE')
for name in ('upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r'):
    a=source_rig.matrix_world@source_rig.data.bones[name].head_local
    b=rig.matrix_world@rig.data.bones[name].head_local
    if (a-b).length>.0001:raise RuntimeError('V9 bind mismatch '+name)
skin.data.transform(skin.matrix_world,shape_keys=True)
skin.parent=rig;skin.matrix_parent_inverse=Matrix.Identity(4);skin.matrix_world=Matrix.Identity(4)
for mod in skin.modifiers:
    if mod.type=='ARMATURE':mod.object=rig
for o in imported-{skin}:bpy.data.objects.remove(o,do_unlink=True)
for i,name in enumerate(('Skin_UpperArm','Skin_Forearm','Skin_Hand')):
    skin.data.materials[i]=material(name)
skin.name="SK_Manny_Arms_Export"
parts={}
for f in sorted((ROOT/"Geometry").glob("*.npz")):
    key=f.stem
    if key in ("Glass","Optic","HoloGlass","HoloReticle","MagnifierYoke"):continue
    d=np.load(f)
    mesh=bpy.data.meshes.new("M249_"+key)
    xf=base.copy()
    # Fold both legs toward the muzzle around their original hinge. Source -X
    # is forward; keep the support bracket on its authored mounting point.
    if key in ("LegLeft","LegRight"):
        pos=d["positions"]
        anchor=Vector(pos[pos[:,2]>pos[:,2].max()-.009].mean(0))
        foot=Vector(pos[pos[:,2]<pos[:,2].min()+.011].mean(0))
        direction=(foot-anchor).normalized()
        target=Vector((-1,.08 if key=="LegRight" else -.08,-.11)).normalized()
        xf=base@Matrix.Translation(anchor)@direction.rotation_difference(target).to_matrix().to_4x4()@Matrix.Translation(-anchor)
    mesh.from_pydata([xf@Vector(v) for v in d["positions"]],[],d["faces"].tolist())
    mesh.update()
    uv=mesh.uv_layers.new(name="UVMap")
    corner=np.empty(len(mesh.loops),dtype=np.int32)
    mesh.loops.foreach_get("vertex_index",corner)
    coords=d["uv"][corner].copy()
    coords[:,1]=1-coords[:,1]
    uv.data.foreach_set("uv",coords.astype(np.float32).ravel())
    mesh.polygons.foreach_set("use_smooth",np.ones(len(mesh.polygons),dtype=bool))
    normals=d["normals"]@np.asarray(xf.to_3x3()).T
    mesh.normals_split_custom_set_from_vertices(normals.tolist())
    o=bpy.data.objects.new("M249_"+key,mesh)
    bpy.context.scene.collection.objects.link(o)
    bone={"Box":"PKM_Box","Cover":"PKM_Cover","Optic":"PKM_Cover","Magnifier":"PKM_Cover","MagnifierYoke":"PKM_Cover",
          "HoloGlass":"PKM_Cover","HoloReticle":"PKM_Cover","MagnifierGlass":"PKM_Cover",
          "Handle":"PKM_Charge","Tray":"PKM_Tray","Trigger":"PKM_Trigger"}.get(key,"WPN_root")
    name={"Box":"M249_Surface__OldBox","Glass":"M249_Glass","LegLeft":"M249_Bipod","LegRight":"M249_Bipod","BipodMount":"M249_Bipod"}.get(key,"M249_Surface")
    if key.startswith("Magnifier"):name="M249_MagnifierGlass" if key=="MagnifierGlass" else "M249_OpticalHousing"
    if key in ("HoloGlass","HoloReticle"):name="M249_"+key
    if key=="Optic":name="M249_HoloHousing"
    if name=="M249_Surface":name="M249_Factory_"+key
    slot(o,name)
    bind_rigid(o,bone)
    parts[key]=o
    components.append(o)
    if key=="Box":
        new=o.copy()
        new.data=o.data.copy()
        bpy.context.scene.collection.objects.link(new)
        new.name="M249_ReplacementBox"
        slot(new,"M249_Surface__NewBox")
        bind_rigid(new,"New_PKM_Box")
        components.append(new)

sys.path.insert(0,str(ROOT/"Repair04"))
sys.path.insert(0,str(ROOT/"Repair05"))
from optic_geometry import align_optics
align_optics(parts,components,rig,bind_rigid,slot)

# Match the catalogue/workbench plane used by existing weapon recipes.
groups={"body":["Receiver"],"barrel":["Barrel"],"muzzle":["Muzzle"],"stock":["Stock"],
        "cover":["Cover"],"magnifier":["Magnifier","MagnifierGlass","MagnifierReticle"],
        "box":["Box"],"bipod":["BipodMount","LegLeft","LegRight"],"handguard":["Handguard"],
        "foregrip":["Foregrip"],"reargrip":["RearGrip"],"trigger":["Trigger"],"handle":["Handle"],
        "tray":["Tray"],"carry":["Carry"]}
labels={"barrel":"原厂枪管","muzzle":"原厂枪口","stock":"原厂枪托","cover":"机匣盖","magnifier":"原厂后置倍镜",
        "box":"原厂弹箱","bipod":"原厂脚架","handguard":"原厂护木","foregrip":"原厂前握把",
        "reargrip":"原厂后握把","trigger":"原厂扳机","handle":"原厂拉机柄","tray":"供弹托盘","carry":"原厂提把"}
recipe={"id":"assemble_m249","output":"ue_m249","inputs":[{"item":"ironIngot","count":5},{"item":"search_assembly_component_box","count":3},{"item":"search_precision_mechanism","count":2}],
        "camera":[20,0,215],"look_at":[75,0,99],"position_tolerance_cm":5,"angle_tolerance_deg":18,"calibration_seconds":34,"parts":[]}
def select(objects):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
def export(objects,name):
    select(objects)
    bpy.ops.export_scene.fbx(filepath=str(EXPORT/(name+".fbx")),use_selection=True,axis_forward="-Y",axis_up="Z",bake_anim=False,
        add_leaf_bones=False,object_types={"MESH"},use_mesh_modifiers=True,mesh_smooth_type="FACE",path_mode="STRIP")
allpts=np.vstack([np.asarray([v.co[:] for v in o.data.vertices]) for o in parts.values()])
# Table UE X follows height of the side silhouette; UE Y follows weapon length.
def table(p):return Vector((p.z,-p.y,p.x))
low=np.asarray([table(Vector(v))[:] for v in allpts]).min(0)
high=np.asarray([table(Vector(v))[:] for v in allpts]).max(0)
offset=Vector((.82-(high[0]+low[0])*.5,-(high[1]+low[1])*.5,.97-low[2]))
for key,ids in groups.items():
    temps=[]
    for part in ids:
        original=parts[part]
        obj=original.copy();obj.data=original.data.copy();bpy.context.scene.collection.objects.link(obj)
        obj.parent=None;obj.matrix_world=Matrix.Identity(4)
        for m in list(obj.modifiers):obj.modifiers.remove(m)
        # skin material slot suffixes separate visibility only; static pieces use the same atlas.
        temps.append(obj)
    select(temps)
    bpy.ops.object.join()
    obj=bpy.context.object
    pts=np.asarray([(table(v.co)+offset)[:] for v in obj.data.vertices])
    center=(pts.min(0)+pts.max(0))*.5
    extent=(pts.max(0)-pts.min(0))*50
    # Apply table rotation to normals as well as vertex positions.
    xf=Matrix([[0,0,1,0],[0,1,0,0],[1,0,0,0],[0,0,0,1]])
    xf.translation=Vector((offset.x-center[0],-offset.y+center[1],offset.z-center[2]))
    obj.data.transform(xf)
    obj.data.flip_normals()
    name="SM_M249_"+key
    export([obj],name)
    bpy.data.objects.remove(obj,do_unlink=True)
    path="/Game/Weapons/M249/Assembly/"+name
    if key=="body":
        recipe.update(body_mesh=path,body_position=(center*100).tolist())
    else:
        i=len(recipe["parts"])
        recipe["parts"].append(dict(id=key,name=labels[key],mesh=path,target=(center*100).tolist(),extent=extent.tolist(),
             loose=[45+(i%2)*80,-65+(i//2)*21,95.4+extent[2]],angle=[-12,20,-15,38,22,-18,30][i%7],radius=max(3.5,min(extent[0],extent[1])+1.5)))
from factory_layout import layout
layout(recipe)
(ROOT/"assembly.json").write_text(json.dumps(recipe,ensure_ascii=False,indent=2),encoding="utf8")
sys.path.insert(0,str(PKM/"Belt08"))
from mesh_export import export_mesh
export_mesh(rig,EXPORT/"SK_M249_V7.fbx")
# Preserve a clean rest-pose editable file; baked actions are authored in UE native space.
for p in bpy.data.actions:p.use_fake_user=False
bpy.ops.outliner.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"M249_Editable.blend"),compress=True)
print("M249_GEOMETRY",len(parts),len(components),flush=True)
