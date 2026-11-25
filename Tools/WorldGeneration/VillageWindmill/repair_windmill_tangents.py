"""Prepare an import copy with valid tangent frames on isolated bad FBX corners.

Run in Blender background with --python-exit-code 1 --python this_file -- input.fbx output.fbx.
The source mesh, its UVs and all valid exported corner frames are preserved.
"""
from pathlib import Path
import shutil
import sys

from io_scene_fbx import encode_bin, parse_fbx
import numpy as np


PROPERTY_WRITERS = {
    "B": "bool", "C": "char", "Z": "int8", "Y": "int16", "I": "int32",
    "L": "int64", "F": "float32", "D": "float64", "R": "bytes", "S": "string",
    "i": "int32_array", "l": "int64_array", "f": "float32_array",
    "d": "float64_array", "b": "bool_array", "c": "byte_array",
}


def child(node, name):
    return next(item for item in node.elems if item.id == name.encode("ascii"))


def array(node, name, width):
    return np.asarray(child(node, name).props[0]).reshape(-1, width)


def layer_values(geometry, positions, layer_name, data_name, width):
    layer = child(geometry, layer_name)
    data = array(layer, data_name, width)
    if child(layer, "ReferenceInformationType").props[0] == b"IndexToDirect":
        data = data[array(layer, data_name + "Index", 1).ravel()]
    if child(layer, "MappingInformationType").props[0] == b"ByVertice":
        data = data[positions]
    return data


def encoded(node):
    result = encode_bin.FBXElem(node.id)
    for code, value in zip(node.props_type, node.props):
        getattr(result, "add_" + PROPERTY_WRITERS[chr(code)])(value)
    result.elems = [encoded(item) for item in node.elems]
    return result


def repair(geometry):
    # The Blender mill exchange stores tangent and binormal arrays directly per corner.
    t_layer, b_layer = (child(geometry, "LayerElement" + name) for name in ("Tangent", "Binormal"))
    for layer in (t_layer, b_layer):
        if (child(layer, "MappingInformationType").props[0] != b"ByPolygonVertex" or
                child(layer, "ReferenceInformationType").props[0] != b"Direct"):
            raise ValueError("Expected direct Blender per-corner tangent frames")
    tangents = array(t_layer, "Tangents", 3)
    binormals = array(b_layer, "Binormals", 3)
    bad = (np.max(np.abs(tangents), axis=1) <= 1e-4) | (np.max(np.abs(binormals), axis=1) <= 1e-4)
    if not np.any(bad):
        return 0
    indices = array(geometry, "PolygonVertexIndex", 1).ravel().copy()
    if not np.all(indices.reshape(-1, 3)[:, 2] < 0):
        raise ValueError("Expected triangulated windmill geometry")
    indices[indices < 0] ^= -1
    positions = array(geometry, "Vertices", 3)[indices]
    uvs = layer_values(geometry, indices, "LayerElementUV", "UV", 2)
    normals = layer_values(geometry, indices, "LayerElementNormal", "Normals", 3)
    for corner in np.flatnonzero(bad):
        first = int(corner) // 3 * 3
        face = slice(first, first + 3)
        p0, p1, p2 = positions[face]
        uv0, uv1, uv2 = uvs[face]
        du1, dv1 = uv1 - uv0
        du2, dv2 = uv2 - uv0
        determinant = du1 * dv2 - du2 * dv1
        normal = normals[corner]
        normal = normal / np.linalg.norm(normal)
        if abs(determinant) > 1e-15:
            along_u = ((p1 - p0) * dv2 - (p2 - p0) * dv1) / determinant
            along_v = ((p2 - p0) * du1 - (p1 - p0) * du2) / determinant
        else:
            # A collapsed ear can share its neighbors' frame even without a UV derivative.
            peer = first + int(np.argmax(np.linalg.norm(tangents[face], axis=1)))
            along_u, along_v = tangents[peer], binormals[peer]
        tangent = along_u - normal * np.dot(normal, along_u)
        if np.linalg.norm(tangent) < 1e-12:
            tangent = np.cross(np.eye(3)[np.argmin(np.abs(normal))], normal)
        tangent /= np.linalg.norm(tangent)
        binormal = np.cross(normal, tangent)
        if np.dot(binormal, along_v) < 0:
            binormal *= -1
        tangents[corner], binormals[corner] = tangent, binormal
    return int(np.count_nonzero(bad))


def prepare(source, destination):
    root, version = parse_fbx.parse(str(source))
    geometry = child(child(root, "Objects"), "Geometry")
    count = repair(geometry)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix(".partial.fbx")
    if count:
        with encode_bin.FBXElem.enable_multithreading_cm():
            tree = encoded(root)
        encode_bin.write(str(temp), tree, version)
    else:
        shutil.copyfile(source, temp)
    temp.replace(destination)
    print(f"WINDMILL_TANGENTS {source.stem} repaired_corners={count}", flush=True)


if __name__ == "__main__":
    source, destination = sys.argv[sys.argv.index("--") + 1:]
    prepare(Path(source), Path(destination))
