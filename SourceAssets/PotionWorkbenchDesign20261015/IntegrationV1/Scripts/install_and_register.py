"""Install only the new asset folder and append the workbench to the active palette.

Run through Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript while the
existing FPSGAME editor is idle. No maps, game sessions or tests are opened.
"""
from pathlib import Path
import datetime,hashlib,json,math,shutil
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[2]
DEST="/Game/Building/PotionWorkbench20261015/V1"
PALETTE="/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
ID="potion_workbench"
E=u.EditorAssetLibrary
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():
    raise RuntimeError("Wrong project; preserve active editor.")
commandlet="-run=pythonscript" in u.SystemLibrary.get_command_line().casefold()
if commandlet:
    if "-PotionWorkbenchRegister" not in u.SystemLibrary.get_command_line():
        raise RuntimeError("Use the explicit PotionWorkbenchRegister commandlet invocation.")
else:
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not level or level.is_in_play_in_editor():
        raise RuntimeError("Current editor is playing; registration requires idle editor.")
if any(p.get_name()==PALETTE for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError("Building palette has unsaved edits; preserve current state.")
imported=json.loads((ROOT/"Receipts/ue-import.json").read_text("utf8"))
if imported["stage"]!="staged_assets_saved":
    raise RuntimeError("Import/save must finish before registration.")
source=ROOT/"UEImportHost/Content/Building/PotionWorkbench20261015/V1"
destination=PROJECT/"Content/Building/PotionWorkbench20261015/V1"
files=sorted(p for p in source.rglob("*") if p.is_file() and p.suffix in (".uasset",".uexp",".ubulk"))
if not files:raise RuntimeError("No staged assets.")
for p in files:
    target=destination/p.relative_to(source)
    if target.exists() and target.read_bytes()!=p.read_bytes():
        raise RuntimeError("Existing asset differs; preserve "+str(target))
installed=[]
for p in files:
    target=destination/p.relative_to(source)
    if not target.exists():
        target.parent.mkdir(parents=True,exist_ok=True)
        with p.open("rb") as src,target.open("xb") as dst:shutil.copyfileobj(src,dst)
    installed.append(str(target.relative_to(PROJECT)))
(ROOT/"Receipts/installation.json").write_text(json.dumps({"stage":"new_packages_installed","files":installed},indent=2),"utf8")
registry=u.AssetRegistryHelpers.get_asset_registry()
registry.scan_paths_synchronous([DEST],force_rescan=True)
mesh=u.load_asset(DEST+"/Meshes/SM_PotionWorkbench")
palette=u.load_asset(PALETTE)
if not isinstance(mesh,u.StaticMesh) or not palette:raise RuntimeError("Imported mesh or current palette unavailable.")
if E.get_metadata_tag(mesh,"PotionWorkbench.Owner")!="PotionWorkbench20261015_IntegrationV1":
    raise RuntimeError("Unexpected mesh ownership.")
u.load_module("StaticMeshEditor")
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
if SM.get_convex_collision_count(mesh)<=0:raise RuntimeError("Buildable requires the authored simple collision.")
body=mesh.get_editor_property("body_setup")
if body.get_editor_property("collision_trace_flag")==u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE:
    raise RuntimeError("Falling prefab cannot use complex-as-simple collision.")
entries=list(palette.get_editor_property("components"))
ids=[str(e.id).casefold() for e in entries]
if ID in ids:
    prior=entries[ids.index(ID)]
    if prior.mesh!=mesh:
        raise RuntimeError("Existing potion workbench points elsewhere; preserve it.")
    raise RuntimeError("Potion workbench already registered; preserve saved entry.")
bounds=mesh.get_bounds();ext=bounds.box_extent
dimensions=[ext.x*2,ext.y*2,ext.z*2]
cells=[max(1,math.ceil(v/20-1e-4)) for v in dimensions]
offset=[0,0,ext.z-cells[2]*10]
entry=u.VoxelBuildPrefab()
entry.set_editor_property("id",u.Name(ID))
entry.set_editor_property("display_name",u.Text("药水工作台"))
entry.set_editor_property("mesh",mesh)
entry.set_editor_property("material",u.Name(""))
entry.set_editor_property("mount",u.VoxelPrefabMount.FREE)
entry.set_editor_property("footprint",u.IntVector(*cells))
entry.set_editor_property("pivot_offset_cm",u.Vector(*offset))
stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
backups=ROOT/"Receipts"/("Registration_"+stamp)
backups.mkdir()
palette_file=PROJECT/"Content/Building/Voxels/Rounded/DA_VoxelBuildPalette.uasset"
originals={p:p.read_bytes() for p in (palette_file,palette_file.with_suffix(".uexp"),palette_file.with_suffix(".ubulk")) if p.exists()}
for p,data in originals.items():(backups/p.name).write_bytes(data)
if any(p.read_bytes()!=data for p,data in originals.items()):
    raise RuntimeError("Palette changed on disk before write; preserve it.")
palette.modify()
palette.set_editor_property("components",entries+[entry])
if not E.save_loaded_asset(palette,False):raise RuntimeError("Palette save failed; backup preserved.")
report={"stage":"registered_saved","id":ID,"name":"药水工作台","menu":"B → 其他 → 药水工作台",
    "palette":PALETTE,"mesh":mesh.get_path_name(),"material_group":"","surface_override":None,
    "actor_class":None,"placement":"existing static prefab; free placement; generic removal/save/replication",
    "dimensions_cm":dimensions,"footprint_cells":cells,"pivot_offset_cm":offset,
    "convex_collision_count":SM.get_convex_collision_count(mesh),"lod_count":SM.get_lod_count(mesh),
    "material_slots":[{"slot":str(s.material_slot_name),"material":s.material_interface.get_path_name()} for s in mesh.static_materials],
    "original_entry_count":len(entries),"new_entry_count":len(entries)+1,"installed_package_files":len(installed),
    "palette_backup":str(backups),"palette_saved_sha256":hashlib.sha256(palette_file.read_bytes()).hexdigest(),
    "registration_mode":"offline_commandlet" if commandlet else "mutex_bridge",
    "new_cpp":False,"maps_saved":False,"runtime_tested":False,"potion_crafting_implemented":False}
(ROOT/"Receipts/registration.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),"utf8")
u.log("POTION_WORKBENCH_REGISTERED "+json.dumps({"menu":report["menu"],"footprint":cells,"lods":report["lod_count"],"hulls":report["convex_collision_count"]},ensure_ascii=False))
