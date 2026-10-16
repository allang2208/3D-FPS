"""Preserve authored LOD0, consolidate a static buildable and author collision/LODs."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent/"ModelV1"
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/"Export/PotionWorkbench_Assembly.blend"),load_ui=False,use_scripts=False)
scene=bpy.context.scene
objects=[o for o in scene.objects if o.type=="MESH"]
bpy.ops.object.select_all(action="DESELECT")
for o in objects:o.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
bpy.ops.object.join()
mesh=bpy.context.object;mesh.name="SM_PotionWorkbench"
scene.cursor.location=(0,0,0)
bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
slots=list(mesh.data.materials);mats=[];mapping={}
for i,m in enumerate(slots):
    if m not in mats:mats.append(m)
    mapping[i]=mats.index(m)
indices=[mapping[f.material_index] for f in mesh.data.polygons]
mesh.data.materials.clear()
for m in mats:mesh.data.materials.append(m)
for f,i in zip(mesh.data.polygons,indices):f.material_index=i

material_specs=[]
for mat in mats:
    p=next(n for n in mat.node_tree.nodes if n.type=="BSDF_PRINCIPLED")
    spec={"slot":mat.name,
          "base_color":list(p.inputs["Base Color"].default_value)[:3],
          "metallic":p.inputs["Metallic"].default_value,
          "roughness":p.inputs["Roughness"].default_value,
          "transmission":p.inputs["Transmission Weight"].default_value,
          "emission_color":list(p.inputs["Emission Color"].default_value)[:3],
          "emission_strength":p.inputs["Emission Strength"].default_value,
          "textures":{}}
    for n in mat.node_tree.nodes:
        if n.type=="TEX_IMAGE" and n.image:
            basename=Path(n.image.filepath).name
            role="BaseColor" if "BaseColor" in basename or "Labels" in basename else "Normal" if "Normal" in basename else "ORM" if "ORM" in basename else "Roughness"
            spec["textures"][role]=str(SOURCE/"Textures"/basename)
    material_specs.append(spec)

collisions=[]
def collision_box(center,size):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center)
    ob=bpy.context.object;ob.name=f"UCX_SM_PotionWorkbench_{len(collisions):02d}"
    ob.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    collisions.append(ob)
    return ob

# The L-shaped support surfaces and pedestals leave the inner standing space open.
collision_box((130,35,91.5),(260,70,5))
collision_box((225,165,91.5),(70,190,5))
for x,y in ((4,4),(4,66),(50,4),(50,66),(194,4),(256,4),(194,70),(194,142),(256,142),(194,256),(256,256)):
    collision_box((x,y,44.5),(5,5,89))
collision_box((27,35,50),(46,61,70))
collision_box((225,221,50),(62,68,70))
collision_box((225,106,56),(60,58,70))
collision_box((225,222,110),(54,53,29))
# Convex approximation of the pot exterior; no giant hull across the L opening.
bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=1,location=(225,106,108))
pot=bpy.context.object;pot.name=f"UCX_SM_PotionWorkbench_{len(collisions):02d}"
pot.scale=(27.5,27.5,19);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);collisions.append(pot)
collision_box((128,11.5,108),(124,16,23))

def select(items):
    bpy.ops.object.select_all(action="DESELECT")
    for o in items:o.select_set(True)
    bpy.context.view_layer.objects.active=items[0]

def export(ob,lod,with_collision=False):
    select([ob]+(collisions if with_collision else []))
    path=ROOT/"Authored"/f"SM_PotionWorkbench_LOD{lod}.fbx"
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={"MESH"},
        apply_unit_scale=True,apply_scale_options="FBX_SCALE_UNITS",axis_forward="-Y",axis_up="Z",
        mesh_smooth_type="FACE",use_tspace=True,add_leaf_bones=False,bake_anim=False,path_mode="STRIP")
    ob.data.calc_loop_triangles()
    return {"lod":lod,"source":str(path),"triangles":len(ob.data.loop_triangles)}

records=[export(mesh,0,True)]
for lod,ratio in ((1,.52),(2,.22)):
    ob=mesh.copy();ob.data=mesh.data.copy();scene.collection.objects.link(ob);ob.name=f"SM_PotionWorkbench_LOD{lod}"
    select([ob])
    mod=ob.modifiers.new("Distance LOD preserving material borders","DECIMATE")
    mod.ratio=ratio;mod.use_collapse_triangulate=True;mod.delimit={"MATERIAL","SEAM","SHARP"}
    bpy.ops.object.modifier_apply(modifier=mod.name)
    records.append(export(ob,lod))
    bpy.data.objects.remove(ob,do_unlink=True)
select([mesh])
for o in collisions:o.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"Authored/PotionWorkbench_Buildable.blend"))
points=[mesh.matrix_world@v.co for v in mesh.data.vertices]
manifest={"id":"potion_workbench","display_name":"药水工作台","menu":"other","material_group":"",
          "mesh":"SM_PotionWorkbench","units":"cm","lods":records,"collision_hulls":len(collisions),
          "materials":material_specs,
          "bounds_min_cm":[min(v[i] for v in points) for i in range(3)],
          "bounds_max_cm":[max(v[i] for v in points) for i in range(3)],
          "source":"../ModelV1/Export/PotionWorkbench_Assembly.blend",
          "lod0_geometry_preserved":True,"rendered":False,"tested":False}
(ROOT/"buildable_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),"utf8")
print("POTION_BUILDABLE_AUTHORED",json.dumps({"lods":records,"collision_hulls":len(collisions)}),flush=True)
