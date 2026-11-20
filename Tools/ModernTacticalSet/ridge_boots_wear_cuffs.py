"""Capture the actual cloth triangles at the boot shaft in each installed trouser option."""
import gc
import gzip
import json
from pathlib import Path
import sys

import unreal as u

sys.path.insert(0, str(Path(__file__).parent))
from coyote_glove_wear_bind import extract
from ridge_boots_wear import WEAR, package_path, plan, sha


def calf_surface(path):
    asset = u.load_asset(path)
    dm = extract(asset)
    q, arrays = u.GeometryScript_MeshQueries, u.GeometryScript_List
    _, positions, _ = q.get_all_vertex_positions(dm, False)
    _, indices, _ = q.get_all_triangle_indices(dm, False)
    _, materials, _ = u.GeometryScript_Materials.get_all_triangle_material_i_ds(dm)
    points = arrays.convert_vector_list_to_array(positions)
    hidden = {i for i, m in enumerate(asset.materials)
              if str(m.material_slot_name).startswith("NATIVE:") or
              (m.material_interface and "body_baked" in m.material_interface.get_name().lower())}
    remap, vertices, faces = {}, [], []
    for face, material in zip(arrays.convert_triangle_list_to_array(indices), arrays.convert_index_list_to_array(materials)):
        ids = (face.x, face.y, face.z)
        if material in hidden or min(points[i].z for i in ids) > 40 or max(points[i].z for i in ids) < 7:
            continue
        for i in ids:
            if i not in remap:
                remap[i] = len(vertices)
                v = points[i]
                vertices.append([round(v.x, 5), round(v.y, 5), round(v.z, 5)])
        faces.append([remap[i] for i in ids])
    return {"asset_sha256": sha(package_path(path)), "positions": vertices, "triangles": faces}


def main():
    for body, row in plan().items():
        output = WEAR / (body + "-cuffs.json.gz")
        capture = {}
        if output.exists():
            with gzip.open(output, "rt", encoding="utf-8") as f:
                capture = json.load(f)
        for routes in row["pants"].values():
            for path in routes.values():
                if capture.get(path, {}).get("asset_sha256") == sha(package_path(path)):
                    continue
                capture[path] = calf_surface(path)
                gc.collect()
                u.SystemLibrary.collect_garbage()
        staging = output.with_suffix(".writing")
        with gzip.open(staging, "wt", compresslevel=5, encoding="utf-8") as f:
            json.dump(capture, f, separators=(",", ":"))
        staging.replace(output)


if __name__ == "__main__":
    main()
