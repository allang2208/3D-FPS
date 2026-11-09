"""Read the saved LOD0 surface and compressed game clips for the belt-contact review."""
from pathlib import Path
import pickle
import unreal as u

out = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_saved_dir())) / "M249ReloadReview"
out.mkdir(exist_ok=True)
prefix = "/Game/Weapons/M249"
mesh = u.load_asset(prefix + "/SK_M249_V7")
dm, result = u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
    mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
if result != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError("Cannot read M249 mesh")
Q = u.GeometryScript_MeshQueries
B = u.GeometryScript_BoneWeights
L = u.GeometryScript_List
_, bones = B.get_all_bones_info(dm)
bones = sorted(bones, key=lambda b: b.index)
_, p, _ = Q.get_all_vertex_positions(dm, False)
_, f, _ = Q.get_all_triangle_indices(dm, False)
vertices = [v.to_tuple() for v in L.convert_vector_list_to_array(p)]
faces = [(v.x, v.y, v.z) for v in L.convert_triangle_list_to_array(f)]
sections = [u.GeometryScript_Materials.get_triangle_material_id(dm, i)[0] for i in range(len(faces))]
weights = []
for i in range(len(vertices)):
    _, raw, valid = B.get_vertex_bone_weights(dm, i)
    if not valid:
        raise RuntimeError(f"Missing weights at vertex {i}")
    weights.append([(w.bone_index, w.weight) for w in raw if w.weight > 0])

def tr(t):
    return (*t.translation.to_tuple(), t.rotation.x, t.rotation.y, t.rotation.z,
            t.rotation.w, *t.scale3d.to_tuple())

used = sorted({i for row in weights for i, _ in row})
by_id = {b.index: b for b in bones}
with (out / "geometry.pkl").open("wb") as handle:
    pickle.dump(dict(vertices=vertices, faces=faces, sections=sections, weights=weights,
                     slots=[str(m.material_slot_name) for m in mesh.materials], used=used,
                     names=[str(by_id[i].name) for i in used],
                     bind=[tr(by_id[i].world_transform) for i in used]), handle)

opts = u.AnimPoseEvaluationOptions()
opts.optional_skeletal_mesh = mesh
opts.evaluation_type = u.AnimDataEvalType.COMPRESSED
for role in ("idle", "reload", "reload_empty"):
    seq = u.load_asset(prefix + "/Animations/A_M249_" + role)
    count = u.AnimationLibrary.get_num_frames(seq) if role != "idle" else 0
    times = [u.AnimationLibrary.get_time_at_frame(seq, i) for i in range(count + 1)]
    frames = []
    for time in times:
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(seq, time, opts)
        frames.append([tr(u.AnimPoseExtensions.get_bone_pose(pose, by_id[i].name, u.AnimPoseSpaces.WORLD))
                       for i in used])
    with (out / (role + ".pkl")).open("wb") as handle:
        pickle.dump((times, frames), handle)
    print("M249_REVIEW_EXTRACT", role, len(times), times[-1], flush=True)
