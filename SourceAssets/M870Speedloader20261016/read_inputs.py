"""Read-only inputs for the M870 speedloader (commandlet, UE closed or via batch gate).

Writes inputs.json (skeletons, sampled clips) and geometry.json (gun surfaces,
Super90 guide, loader props bind). Never saves or dirties assets.
"""
import json, hashlib, gc
from pathlib import Path
import unreal as u

O = Path(__file__).parent; P = O.parents[1]
S90_MESH = '/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7'
M870_MESH = '/Game/Weapons/M870/Tactical20261015/SK_M870_V7'
S90_LOADER = '/Game/Weapons/Super90/Speedloader20261007/Animations/A_Super90_loader_'
S90_ANIM = '/Game/Weapons/Super90/Cransh20261006/Animations/A_Super90_'
M870_ANIM = '/Game/Weapons/M870/Tactical20261015/Animations/A_M870_'
GUIDE = '/Game/Weapons/Super90/Speedloader20261007/SM_Super90_LoaderGuide'
PROPS = '/Game/Weapons/Super90/Speedloader20261007/SK_Super90_LoaderProps'
G = u.GeometryScript_AssetUtils; Q = u.GeometryScript_MeshQueries; Bw = u.GeometryScript_BoneWeights


def sha(path):
    return hashlib.sha256((P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')).read_bytes()).hexdigest()


def tf(t):
    return [*t.translation.to_tuple(), t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w, *t.scale3d.to_tuple()]


def skeleton(mesh_path):
    mesh = u.load_asset(mesh_path)
    comp = u.SkeletalMeshComponent(); comp.set_skeletal_mesh_asset(mesh)
    names = [str(comp.get_bone_name(i)) for i in range(comp.get_num_bones())]
    parents = {n: str(comp.get_parent_bone(n)) for n in names}
    ref = u.AnimPoseExtensions.get_reference_pose(mesh.skeleton)
    local = {n: tf(u.AnimPoseExtensions.get_bone_pose(ref, n, u.AnimPoseSpaces.LOCAL)) for n in names}
    world = {n: tf(u.AnimPoseExtensions.get_bone_pose(ref, n, u.AnimPoseSpaces.WORLD)) for n in names}
    return mesh, dict(path=mesh_path, sha256=sha(mesh_path), names=names, parents=parents, ref_local=local, ref_world=world)


def clips(mesh, names, paths):
    opt = u.AnimPoseEvaluationOptions(); opt.optional_skeletal_mesh = mesh; opt.should_retarget = False
    opt.evaluation_type = u.AnimDataEvalType.SOURCE
    out = {}
    for role, path in paths.items():
        asset = u.load_asset(path)
        if not asset: print('M870_LOADER_INPUT_MISSING', path, flush=True); continue
        frames = u.AnimationLibrary.get_num_frames(asset); duration = asset.get_play_length()
        rows = []
        for i in range(frames + 1):
            pose = u.AnimPoseExtensions.get_anim_pose_at_time(asset, i * duration / frames, opt)
            rows.append({n: tf(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.LOCAL)) for n in names})
        out[role] = dict(path=asset.get_path_name(), sha256=sha(path), frames=frames, duration=duration, rows=rows)
        print('M870_LOADER_INPUT', role, frames, flush=True)
        asset = None; gc.collect()
    return out


def surface(mesh_path, keep_skin=False):
    asset = u.load_asset(mesh_path)
    dm, st = G.copy_mesh_from_skeletal_mesh(asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    _, ps, _ = Q.get_all_vertex_positions(dm, False); ps = u.GeometryScript_List.convert_vector_list_to_array(ps)
    _, ts, _ = Q.get_all_triangle_indices(dm, False); ts = u.GeometryScript_List.convert_triangle_list_to_array(ts)
    _, bones = Bw.get_all_bones_info(dm); bname = {b.index: str(b.name) for b in bones}
    slots = [str(s.material_slot_name) for s in asset.materials]
    tris, mats = [], []
    for ti in range(len(ts)):
        m, ok = u.GeometryScript_Materials.get_triangle_material_id(dm, ti)
        tris.append([ts[ti].x, ts[ti].y, ts[ti].z]); mats.append(m)
    dom = []
    for vi in range(len(ps)):
        _, ws, ok = Bw.get_vertex_bone_weights(dm, vi)
        dom.append(bname[max(ws, key=lambda w: w.weight).bone_index] if ok and ws else '')
    return dict(path=mesh_path, slots=slots, positions=[[p.x, p.y, p.z] for p in ps], triangles=tris, materials=mats, dominant=dom)


s90_mesh, s90 = skeleton(S90_MESH)
m870_mesh, m870 = skeleton(M870_MESH)
props_mesh, props = skeleton(PROPS)
data = dict(super90=s90, m870=m870, props=props)
s90_paths = {('%s_%d' % (b, i)): S90_LOADER + '%s_%d' % (b, i) for b in ('normal', 'empty') for i in range(1, 8)}
s90_paths['cycle'] = S90_LOADER + 'cycle'
s90_paths['idle'] = S90_ANIM + 'idle'
data['super90_clips'] = clips(s90_mesh, s90['names'], s90_paths)
data['m870_clips'] = clips(m870_mesh, m870['names'], {r: M870_ANIM + r for r in ('idle', 'cycle', 'reload_full', 'reload_continuous', 'fire')})
(O / 'inputs.json').write_text(json.dumps(data, separators=(',', ':')))
geo = dict(m870=surface(M870_MESH), super90=surface(S90_MESH), props=surface(PROPS))
gm = u.load_asset(GUIDE)
dm, st = G.copy_mesh_from_static_mesh(gm, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
_, ps, _ = Q.get_all_vertex_positions(dm, False); ps = u.GeometryScript_List.convert_vector_list_to_array(ps)
_, ts, _ = Q.get_all_triangle_indices(dm, False); ts = u.GeometryScript_List.convert_triangle_list_to_array(ts)
geo['super90_guide'] = dict(path=GUIDE, positions=[[p.x, p.y, p.z] for p in ps], triangles=[[t.x, t.y, t.z] for t in ts],
                            materials=[str(m.material_slot_name) for m in gm.static_materials],
                            material_paths=[m.material_interface.get_path_name() if m.material_interface else '' for m in gm.static_materials])
(O / 'geometry.json').write_text(json.dumps(geo, separators=(',', ':')))
print('M870_LOADER_INPUTS_SAVED', flush=True)
