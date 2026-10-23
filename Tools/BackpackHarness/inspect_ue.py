"""Read current clothing, saved harnesses and any already-running player pose."""
import json
from pathlib import Path
import unreal as u

P = Path("D:/FPS3D/FPSGAME")
R = P / "SourceAssets/BackpackHarnessRebuild20261020"
job_file = R / "inspect_job.json"
job = json.loads(job_file.read_text(encoding='utf-8-sig')) if job_file.exists() else {"phase": "before"}
phase = job["phase"]
out = R / ("Inputs" if phase in ("before","refresh") else "SavedReadback")
out.mkdir(parents=True, exist_ok=True)
cfg = json.loads((P / "Content/ColdSteelData/player_body.json").read_text(encoding="utf-8-sig"))
outfits = json.loads((P / "Content/ColdSteelData/modular_outfits.json").read_text(encoding="utf-8-sig"))["items"]
pack = cfg["outfits"]["ue_mountain_backpack"]
Q, G, B, L = u.GeometryScript_MeshQueries, u.GeometryScript_AssetUtils, u.GeometryScript_BoneWeights, u.GeometryScript_List


def vector(v):
    return [v.x, v.y, v.z]


def export(key, path, lod=0):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError("Missing active asset: " + path)
    dm, status = G.copy_mesh_from_skeletal_mesh(
        asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD(lod_index=lod))
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError("Cannot read active asset: " + path)
    _, points, _ = Q.get_all_vertex_positions(dm, False)
    _, faces, _ = Q.get_all_triangle_indices(dm, False)
    points = L.convert_vector_list_to_array(points)
    faces = L.convert_triangle_list_to_array(faces)
    _, bones = B.get_all_bones_info(dm)
    weights = []
    for vi in range(len(points)):
        _, pairs, valid = B.get_vertex_bone_weights(dm, vi)
        if not valid:
            raise RuntimeError("Missing skin weights: " + path)
        weights.append([[pair.bone_index, pair.weight] for pair in pairs if pair.weight > 0])
    data = {
        "source": path, "positions": [vector(v) for v in points], "triangles": [vector(f) for f in faces],
        "weights": weights, "bones": [{"index": b.index, "name": str(b.name), "parent": b.parent_index} for b in bones],
        "reference":{str(b.name):vector(b.world_transform.translation)+
                     [getattr(b.world_transform.rotation,c) for c in 'xyzw']+
                     vector(b.world_transform.scale3d) for b in bones},
        "triangle_materials": [u.GeometryScript_Materials.get_triangle_material_id(dm, i)[0] for i in range(len(faces))],
        "materials": [{"slot": str(m.material_slot_name), "asset": m.material_interface.get_path_name() if m.material_interface else None} for m in asset.materials],
        "revision": u.EditorAssetLibrary.get_metadata_tag(asset, "BackpackHarnessRevision"),
        "source_sha256": u.EditorAssetLibrary.get_metadata_tag(asset, "BackpackHarnessSourceSHA256"),
        "lod":lod,
        "lod_count": u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(asset),
    }
    if phase == "after":
        data["uv"]=[];data["normals"]=[]
        for ti in range(len(faces)):
            a,b,c,valid=Q.get_triangle_u_vs(dm,0,ti)
            _,na,nb,nc,nvalid=Q.get_triangle_normals(dm,ti)
            if not valid or not nvalid:raise RuntimeError("Missing saved UV/normal overlay")
            data["uv"].append([[v.x,v.y] for v in (a,b,c)])
            data["normals"].append([vector(v) for v in (na,nb,nc)])
    suffix="" if lod==0 else "_lod"+str(lod)
    (out / (key + suffix + ".json")).write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    if phase == 'refresh':
        poses_path=R/'Inputs/poses.json'
        poses=json.loads(poses_path.read_text())
        poses['mesh_references'][key]=data['reference']
        poses_path.write_text(json.dumps(poses,separators=(',',':')),encoding='utf-8')
    print("HARNESS_INSPECT_ASSET", key, len(points), len(faces), data["revision"], flush=True)
    del dm, data
    u.SystemLibrary.collect_garbage()


sources = {"backpack_bare": pack["world_mesh"]}
sources.update({"backpack_" + k: v for k, v in pack.get("world_mesh_by_shirt", {}).items()})
if phase in ("before","refresh"):
    sources["body"] = cfg["body_mesh"]
    for name, item in outfits.items():
        if item.get("slot") == 7 and item.get("rig_meshes", {}).get("Jason"):
            sources[name] = item["rig_meshes"]["Jason"]
if phase == 'refresh':
    sources={k:sources[k] for k in job['keys']}
if phase == "after":
    manifest=json.loads((R/"manifest.json").read_text())
    sources={row["profile"]:row["asset"] for row in manifest["variants"]}
for key, path in sources.items():
    count=1 if phase!="after" else u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(u.load_asset(path))
    for lod in range(count):export(key,path,lod)

runtime = []
worlds = u.EditorLevelLibrary.get_pie_worlds(False)
for world in worlds:
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Character):
        if not actor.is_player_controlled():
            continue
        for component in actor.get_components_by_class(u.SkeletalMeshComponent):
            mesh = component.skeletal_mesh_asset
            if not mesh or ("Backpack" not in mesh.get_path_name() and mesh.get_path_name() != cfg["body_mesh"]):
                continue
            row = {"actor": actor.get_name(), "component": component.get_name(), "asset": mesh.get_path_name(),
                   "relative": str(component.get_relative_transform()), "parent": str(component.get_attach_parent()),
                   "visible": component.is_visible(), "bone_transforms": {}}
            for bi in range(component.get_num_bones()):
                name = component.get_bone_name(bi)
                transform = component.get_socket_transform(name, u.RelativeTransformSpace.RTS_COMPONENT)
                row["bone_transforms"][str(name)] = {
                    "translation": vector(transform.translation),
                    "rotation": [transform.rotation.x, transform.rotation.y, transform.rotation.z, transform.rotation.w],
                    "scale": vector(transform.scale3d)}
            runtime.append(row)
(out / "runtime.json").write_text(json.dumps({"pie_active": bool(worlds), "components": runtime}, indent=2), encoding="utf-8")
print("HARNESS_INSPECT_COMPLETE", phase, "pie_active", bool(worlds), "components", len(runtime), flush=True)
