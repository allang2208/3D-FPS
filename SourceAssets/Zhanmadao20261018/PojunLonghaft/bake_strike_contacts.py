"""Bake mesh-local butt contacts for the rigid parts admitted by the dao catalog."""
import json
from pathlib import Path

import unreal as ue


def distal_contact(path):
    mesh = ue.load_asset(path)
    geometry = ue.DynamicMesh()
    _, result = ue.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
        mesh, geometry, ue.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=True),
        ue.GeometryScriptMeshReadLOD(lod_type=ue.GeometryScriptLODType.SOURCE_MODEL, lod_index=0))
    if result != ue.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError(f"Cannot read LOD0 of {path}")
    queries = ue.GeometryScript_MeshQueries
    _, vertices, _ = queries.get_all_vertex_positions(geometry, False)
    _, indices, _ = queries.get_all_triangle_indices(geometry, False)
    points = ue.GeometryScript_List.convert_vector_list_to_array(vertices)
    triangles = ue.GeometryScript_List.convert_triangle_list_to_array(indices)
    low = min(p.z for p in points)
    rim = [p for p in points if p.z <= low + .001]
    x = (min(p.x for p in rim) + max(p.x for p in rim)) / 2
    y = (min(p.y for p in rim) + max(p.y for p in rim)) / 2
    # Use the center of a flat end only if it actually lies on a cap triangle.
    for t in triangles:
        a, b, c = points[t.x], points[t.y], points[t.z]
        if max(a.z, b.z, c.z) > low + .001:
            continue
        cross = (b.x-a.x)*(c.y-a.y) - (b.y-a.y)*(c.x-a.x)
        if abs(cross) < 1e-10:
            continue
        u = ((x-a.x)*(c.y-a.y) - (y-a.y)*(c.x-a.x)) / cross
        v = ((b.x-a.x)*(y-a.y) - (b.y-a.y)*(x-a.x)) / cross
        if min(u, v, 1-u-v) >= -1e-6:
            return [x, y, a.z + u*(b.z-a.z) + v*(c.z-a.z)]
    p = min(rim, key=lambda p: ((p.x-x)**2 + (p.y-y)**2, p.z, p.x, p.y))
    return [p.x, p.y, p.z]


project = Path(ue.Paths.project_dir()).resolve()
data = project / "Content/ColdSteelData"
catalog = json.loads((data / "zhanmadao-modules.json").read_text(encoding="utf-8-sig"))
profile = catalog["pommel_profile"]
library = json.loads((data / profile["library"]).read_text(encoding="utf-8-sig"))
finish = library["finishes"][profile["finish"]]
meshes = [catalog["slots"]["grip"]["pojun_longhaft"]["mesh"], catalog["slots"]["pommel"]["factory"]["mesh"]]
for key, part in library["options"].items():
    if part["interface"] in profile["interfaces"] and "ue_zhanmadao" in part.get("weapons", ["ue_zhanmadao"]):
        meshes.append(finish.get(key, {}).get("mesh", part["mesh"]))
contacts = {path: [round(v, 6) for v in distal_contact(path)] for path in meshes}
(project / "Saved/PojunStrikeContacts.json").write_text(json.dumps(contacts, indent=2), encoding="utf-8")
