"""Author each lower-body distance mesh with its own skin weights and intact panel layers."""
import unreal as u

from coyote_glove_wear_save import io

REVISION = "SewnSkinLOD01"


def meshes(data, reference, prefix):
    original_slots = data["material_slots"]
    for lod, omit in enumerate(({"Thread"}, {"Thread", "Hardware"}), start=1):
        omitted = {prefix + name for name in omit}
        faces = [index for index, slot in enumerate(data["triangle_materials"]) if original_slots[slot] not in omitted]
        pattern = dict(data)
        for key in ("triangles", "triangle_materials", "uv", "normals"):
            pattern[key] = [data[key][index] for index in faces]
        mesh = io.dynamic(pattern, reference)
        options = u.GeometryScriptSimplifyMeshOptions(
            preserve_vertex_positions=True, allow_seam_smoothing=False, allow_seam_splits=False)
        if prefix == "RB_":
            # Keep the outsole and curved vamp silhouette within the previous render budget.
            target = int(len(data["triangles"]) * (.26, .21)[lod - 1])
            u.GeometryScript_MeshSimplification.apply_simplify_to_triangle_count(mesh, target, options)
        yield lod, mesh


def source_lods(asset):
    for lod in (1, 2):
        source = u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL, lod_index=lod)
        mesh, result = u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
            asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), source)
        if result != u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError(f"Cannot read {asset.get_name()} LOD{lod} sewing pattern")
        yield lod, mesh


def write(asset, levels, options):
    for lod, mesh in levels:
        _, result = u.GeometryScript_AssetUtils.copy_mesh_to_skeletal_mesh(
            mesh, asset, options, u.GeometryScriptMeshWriteLOD(lod_index=lod))
        if result != u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError(f"Cannot author {asset.get_name()} LOD{lod}")
