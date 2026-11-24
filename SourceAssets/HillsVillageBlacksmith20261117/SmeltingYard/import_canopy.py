"""Import the smith yard shelter with open walkable bays and a visibility-blocking roof."""
from pathlib import Path
import json
import sys
import unreal as u

src=Path(__file__).resolve().parent
dest="/Game/WorldGeneration/TemperateHills/VillageBlacksmith/SmeltingYard"
name="SM_SmithSmeltingCanopy"
sys.path.insert(0,str(src))
from yard_sites import sockets_cm
from yard_materials import build as build_wear
build_wear(import_fields=not globals().get("use_saved_fields",False))
wear=dest+"/Wear/"
smith="/Game/WorldGeneration/TemperateHills/VillageBlacksmith/"
paths={"Canvas":wear+"M_SmithSmokeCanvas",
       "Oak":wear+"M_SmithWorkedOak",
       "Stone":smith+"Workfloor/Materials/M_SmithHearthStone",
       "Iron":wear+"M_SmithWornIron",
       "Coal":wear+"M_SmithSpentCharcoal",
       "Brick":"/Game/Props/BlastFurnace20260923/Materials/M_BlastFurnace_Firebrick",
       "Clinker":"/Game/Props/BlastFurnace20260923/Materials/M_BlastFurnace_SlagLining",
       "Bark":"/Game/Items/HarvestTimber/M_PoplarSolidBark",
       "End":"/Game/Items/HarvestTimber/M_PoplarSolidEnd",
       "Split":smith+"ArtPassR2/Materials/M_VillageR2_Oak"}
materials={slot:u.load_asset(path) for slot,path in paths.items()}
if not all(materials.values()):
    raise RuntimeError("Missing shelter material: "+str([k for k,v in materials.items() if not v]))
task=u.AssetImportTask()
task.filename=str(src/(name+".fbx"))
task.destination_path=dest
task.destination_name=name
task.automated=True
task.replace_existing=True
task.replace_existing_settings=True
task.save=False
opt=u.FbxImportUI()
opt.automated_import_should_detect_type=False
opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh=True
opt.import_as_skeletal=False
opt.import_materials=False
opt.import_textures=False
data=opt.static_mesh_import_data
data.combine_meshes=True
data.auto_generate_collision=False
data.generate_lightmap_u_vs=True
data.convert_scene=True
data.convert_scene_unit=True
task.options=opt
task.factory=u.FbxFactory()
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mesh=next((obj for obj in task.get_objects() if isinstance(obj,u.StaticMesh) and obj.get_name()==name),None)
if not mesh: raise RuntimeError("Shelter FBX import failed")
# The legacy importer generates lightmaps on UV1. Authored wear is on UV2.
for label,(point,angle) in sockets_cm().items():
    socket=mesh.find_socket(label)
    if not socket:
        socket=u.StaticMeshSocket(outer=mesh)
        socket.set_editor_property("socket_name",label)
        mesh.add_socket(socket)
    socket.set_editor_property("relative_location",u.Vector(*point))
    socket.set_editor_property("relative_rotation",u.Rotator(pitch=angle[0],yaw=angle[1],roll=angle[2]))
for i,slot in enumerate(mesh.static_materials):
    mesh.set_material(i,materials[str(slot.material_slot_name)])
def collider(center,size,pitch=0,yaw=0):
    part=u.KBoxElem()
    part.set_editor_property("center",u.Vector(*center))
    part.set_editor_property("rotation",u.Rotator(pitch=pitch,yaw=yaw,roll=0))
    for axis,value in zip(("x","y","z"),size):
        part.set_editor_property(axis,value)
    return part
boxes=[collider(**entry) for entry in json.loads((src/"collision.json").read_text(encoding="utf-8"))]
body=mesh.get_editor_property("body_setup")
agg=body.get_editor_property("agg_geom")
agg.set_editor_property("convex_elems",[])
agg.set_editor_property("box_elems",boxes)
body.set_editor_property("agg_geom",agg)
body.set_editor_property("collision_trace_flag",u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):
    raise RuntimeError("Failed to save "+mesh.get_path_name())
u.log("SMITH_SMELTING_YARD_SAVED "+mesh.get_path_name())
