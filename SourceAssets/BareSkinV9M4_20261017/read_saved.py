"""Read-only commandlet: verify the saved M4 V9 sample against the install payload. Writes readback.json."""
import json
from pathlib import Path
import unreal as u

R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9M4_20261017')
G = u.GeometryScript_AssetUtils; Q = u.GeometryScript_MeshQueries; Bw = u.GeometryScript_BoneWeights
pay = json.loads((R / 'Work/install_payload.json').read_text())
mesh = u.load_asset(pay['mesh'])
dm, _ = G.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
_, ps, _ = Q.get_all_vertex_positions(dm, False); ps = u.GeometryScript_List.convert_vector_list_to_array(ps)
pos_err = max(max(abs(ps[v].x - p[0]), abs(ps[v].y - p[1]), abs(ps[v].z - p[2])) for v, p in zip(pay['vertex_ids'], pay['positions']))
uv_err = 0.0; n_err = 0.0
vn = {v: n for v, n in zip(pay['vertex_ids'], pay['vertex_normals'])}
_, tris, _ = Q.get_all_triangle_indices(dm, False); tris = u.GeometryScript_List.convert_triangle_list_to_array(tris)
for tid, uv in zip(pay['triangle_ids'][::7], pay['uv0'][::7]):
    a, b, c, ok = Q.get_triangle_u_vs(dm, 0, tid)
    uv_err = max(uv_err, *[abs(x.x - y[0]) + abs(x.y - y[1]) for x, y in zip((a, b, c), uv)])
    _, n0, n1, n2, ok = Q.get_triangle_normals(dm, tid); t = tris[tid]
    for n, v in zip((n0, n1, n2), (t.x, t.y, t.z)):
        e = vn[v]; n_err = max(n_err, 1 - (n.x * e[0] + n.y * e[1] + n.z * e[2]))
_, bones = Bw.get_all_bones_info(dm); names = {b.index: str(b.name) for b in bones}
w_err = 0.0
for vid, row in list(pay['weights'].items())[::5]:
    _, ws, ok = Bw.get_vertex_bone_weights(dm, int(vid)); got = {names[w.bone_index]: w.weight for w in ws if w.weight > 0}
    w_err = max(w_err, max(abs(got.get(b, 0) - row.get(b, 0)) for b in set(got) | set(row)))
tex = {}
for n in ('T_M4SkinV9_Colour', 'T_M4SkinV9_Normal', 'T_M4SkinV9_Masks'):
    t = u.load_asset('/Game/Characters/ModularOutfit20260924/BareSkinV9M4/Textures/' + n)
    tex[n] = dict(srgb=t.get_editor_property('srgb'), compression=str(t.get_editor_property('compression_settings')),
                  size=[t.blueprint_get_size_x(), t.blueprint_get_size_y()])
out = dict(position_err_cm=pos_err, uv0_err=uv_err, normal_1_minus_dot=n_err, weight_err=w_err, bones=len(bones),
           lods=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(mesh),
           morphs=[m.get_name() for m in mesh.get_editor_property('morph_targets')],
           slots=[(str(s.material_slot_name), s.material_interface.get_path_name().split('.')[-1] if s.material_interface else '') for s in mesh.materials],
           textures=tex, tag=u.EditorAssetLibrary.get_metadata_tag(mesh, 'BareSkinV9'))
(R / 'readback.json').write_text(json.dumps(out, indent=1))
print('M4V9_READBACK', json.dumps(out), flush=True)
