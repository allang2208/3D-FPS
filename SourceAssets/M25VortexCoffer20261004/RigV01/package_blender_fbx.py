"""Package the authored M25 rig into editable Blender and FBX files.
Imports the authored GLB as a production conversion, not a validation pass.
No renders, tests, UE operations, or game launch.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix

ROOT=Path(__file__).resolve().parent
ANIMS=ROOT/"Animations";ANIMS.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.fps=30
scene.unit_settings.system="METRIC"
scene.unit_settings.scale_length=1.0
print("PACKAGE importing authored high-poly rig",flush=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/"M25_VortexCoffer_RigV01.glb"),
    merge_vertices=False)
rig=next(o for o in scene.objects if o.type=="ARMATURE")
mesh=next(o for o in scene.objects if o.type=="MESH")
rig.name="RIG_M25_VortexCoffer_V01"
rig.data.name="SKEL_M25_VortexCoffer_V01"
mesh.name="SK_M25_VortexCoffer_V01"
rig.show_in_front=True
rig.data.display_type="OCTAHEDRAL"
spec=json.loads((ROOT/"skeleton_spec.json").read_text(encoding="utf-8"))
contracts=json.loads((ROOT/"animation_contract.json").read_text(encoding="utf-8"))
groups={}
for name in ["Body","GroundSupport","Tendrils","Maw","Electrodes","Sockets"]:
    groups[name]=rig.data.collections.new(name)
for s in spec:
    b=rig.data.bones.get(s["name"])
    if b is None:continue
    region=s["region"]
    collection=("Tendrils" if region.startswith("tendril") else
        "Maw" if region in ("mouth","maw_rim") else
        "Electrodes" if region=="electrode" else
        "Sockets" if region=="socket" else
        "GroundSupport" if region in ("root","belly_support") else "Body")
    groups[collection].assign(b)
    b.use_deform=s["deform"]
    b["anatomy_region"]=region
rig["forward_axis"]="-Y"
rig["up_axis"]="+Z"
rig["nominal_length_m"]=4.1
rig["crawl_reference_speed_m_s"]=.16
rig["crawl_cycle_seconds"]=2.8
rig["skin_max_influences"]=4
rig["source_topology_preserved"]=True
rig["test_status"]="Not tested; no acceptance render or UE import"
mesh["original_triangle_count"]=6524740
mesh["asset_role"]="Preserved high-poly rigging master; not reduced game mesh"
for ob in [rig,mesh]:
    if ob.animation_data:
        for track in ob.animation_data.nla_tracks:track.mute=True
if rig.animation_data is None:rig.animation_data_create()
actions={}
for c in contracts:
    action=next(a for a in bpy.data.actions if a.name==c["name"] or a.name.startswith(c["name"]))
    action.use_fake_user=True
    actions[c["name"]]=action
def activate(name):
    action=actions[name]
    rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    start,end=action.frame_range
    scene.frame_start=int(round(start));scene.frame_end=int(round(end))
    scene.frame_set(scene.frame_start)
    return scene.frame_start,scene.frame_end

bpy.ops.file.pack_all()
activate("M25_Idle")
bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True);mesh.select_set(True)
bpy.context.view_layer.objects.active=rig
scene.render.fps=30
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=="VIEW_3D":
            area.spaces.active.region_3d.view_distance=5.5
            area.spaces.active.region_3d.view_location=(0,0,.60)
            area.spaces.active.shading.type="MATERIAL"
blend=ROOT/"M25_VortexCoffer_RigAndCrawl_V01.blend"
print("PACKAGE saving editable rig and actions",flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
files=[{"file":blend.name,"bytes":blend.stat().st_size,"kind":"editable_blender"}]
def receipt(stage):
    (ROOT/"package_receipt.json").write_text(json.dumps({
        "stage":stage,"files":files,"ue_imported":False,"tested":False,
        "rendered":False,"mesh_role":"original high-poly bound master",
        "forward_axis_blender":"-Y","up_axis_blender":"+Z",
        "fps":30},indent=2),encoding="utf-8")
receipt("blend_saved")
common=dict(use_selection=True,add_leaf_bones=False,use_armature_deform_only=False,
    bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
    bake_anim_use_all_bones=True,bake_anim_force_startend_keying=True,
    bake_anim_step=1.,bake_anim_simplify_factor=0.,
    axis_forward="-Y",axis_up="Z",apply_unit_scale=True,
    apply_scale_options="FBX_SCALE_NONE",use_custom_props=True)
# The large mesh is omitted from animation FBXs. It stays unchanged in the
# separate bound model, GLB and editable source.
bpy.ops.object.select_all(action="DESELECT");rig.select_set(True)
for c in contracts:
    frames=activate(c["name"])
    path=ANIMS/("A_"+c["name"]+".fbx")
    print("PACKAGE exporting "+c["name"],flush=True)
    bpy.ops.export_scene.fbx(filepath=str(path),object_types={"ARMATURE"},
        bake_anim=True,path_mode="AUTO",embed_textures=False,**common)
    files.append({"file":"Animations/"+path.name,"bytes":path.stat().st_size,
        "kind":"animation_fbx","frame_start":frames[0],"frame_end":frames[1],
        "seconds":c["seconds"]})
    receipt("animation_exports")
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
rig.data.pose_position="REST"
bpy.ops.object.select_all(action="DESELECT");rig.select_set(True);mesh.select_set(True)
bpy.context.view_layer.objects.active=rig
model=ROOT/"SK_M25_VortexCoffer_V01.fbx"
print("PACKAGE exporting full-density bound FBX",flush=True)
bpy.ops.export_scene.fbx(filepath=str(model),object_types={"ARMATURE","MESH"},
    bake_anim=False,use_mesh_modifiers=False,mesh_smooth_type="OFF",
    path_mode="COPY",embed_textures=True,**common)
files.append({"file":model.name,"bytes":model.stat().st_size,"kind":"bound_model_fbx"})
receipt("complete")
print("M25_PACKAGE_SAVED",flush=True)
