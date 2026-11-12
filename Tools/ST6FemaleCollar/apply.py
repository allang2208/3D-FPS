"""Shared female ST6 neck production hook; no asset or config side effects on import."""
import json
from pathlib import Path
import unreal as u

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/ST6FemaleCollar20261108')
G, B, Q, L = u.GeometryScript_AssetUtils, u.GeometryScript_BoneWeights, u.GeometryScript_MeshQueries, u.GeometryScript_List


def replace_collar(mesh, materials):
    """Keep source sleeves/waist/UVs and append the head-derived collar."""
    slot = next((i for i, m in enumerate(materials) if m['slot'] == 'ST6NeckAndHemFabric'), None)
    if slot is None:
        return False
    data = json.loads((WORK / 'collar.json').read_text())
    _, bones = B.get_all_bones_info(mesh)
    ids = {str(b.name): b.index for b in bones}
    split, vertices, normals, uv, weights, triangles = {}, [], [], [], [], []
    for fi, face in enumerate(data['triangles']):
        tri = []
        for ci, vi in enumerate(face):
            n, tex = data['normals'][fi][ci], data['uv'][fi][ci]
            key = (vi, *[round(v, 7) for v in n + tex])
            if key not in split:
                split[key] = len(vertices)
                vertices.append(u.Vector(*data['positions'][vi]))
                normals.append(u.Vector(*n))
                uv.append(u.Vector2D(*tex))
                weights.append(data['weights'][vi])
            tri.append(split[key])
        triangles.append(u.IntVector(*tri))
    patch = u.DynamicMesh()
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(patch,
        u.GeometryScriptSimpleMeshBuffers(vertices=vertices, normals=normals, uv0=uv, triangles=triangles), 0, True)
    B.copy_bones_from_mesh(mesh, patch)
    B.mesh_create_bone_weights(patch)
    for vertex, row in enumerate(weights):
        _, success = B.set_vertex_bone_weights(patch, vertex,
            [u.GeometryScriptBoneWeight(bone_index=ids[name], weight=w) for name, w in row.items()])
        if not success:
            raise RuntimeError('Cannot bind female collar vertex')
    for fi in range(len(triangles)):
        u.GeometryScript_Materials.set_triangle_material_id(patch, fi, slot, True)
    _, positions, _ = Q.get_all_vertex_positions(mesh, False)
    _, source_faces, _ = Q.get_all_triangle_indices(mesh, False)
    positions = L.convert_vector_list_to_array(positions)
    source_faces = L.convert_triangle_list_to_array(source_faces)
    remove = [i for i, f in enumerate(source_faces)
              if u.GeometryScript_Materials.get_triangle_material_id(mesh, i)[0] == slot
              and min(positions[v].z for v in (f.x, f.y, f.z)) > 120.]
    _, removed = u.GeometryScript_MeshEdits.delete_triangles_from_mesh(
        mesh, L.convert_array_to_index_list(remove), True)
    if removed != len(remove) or not remove:
        raise RuntimeError('Cannot remove old female neck component')
    u.GeometryScript_MeshEdits.append_mesh(mesh, patch, u.Transform(), False)
    return True


def configure_lods(asset):
    """Use a separate immutable full-detail neckline policy on all three LODs."""
    destination = '/Game/Characters/ModularOutfit20260924/ST6FemaleCollar20261108'
    name = 'DA_Kaitlin_ST6_NeckLODPolicy'
    policy = u.load_asset(destination + '/' + name)
    if not policy:
        factory = u.DataAssetFactory()
        factory.set_editor_property('data_asset_class', u.SkeletalMeshLODSettings)
        policy = u.AssetToolsHelpers.get_asset_tools().create_asset(name, destination, u.SkeletalMeshLODSettings, factory)
        groups = []
        for screen in (1., .18, .075):
            group = u.SkeletalMeshLODGroupSettings()
            settings = group.get_editor_property('reduction_settings')
            for key, value in dict(num_of_triangles_percentage=1., num_of_vert_percentage=1., max_bones_per_vertex=8,
                lock_edges=True, enforce_bone_boundaries=True, merge_coincident_vert_bones=False,
                welding_threshold=0., recalc_normals=False).items():
                settings.set_editor_property(key, value)
            group.set_editor_property('reduction_settings', settings)
            group.set_editor_property('screen_size', u.PerPlatformFloat(default=screen))
            groups.append(group)
        policy.set_editor_property('lod_groups', groups)
        if not u.EditorAssetLibrary.save_loaded_asset(policy, False):
            raise RuntimeError('Cannot save female collar LOD policy')
    groups = list(policy.get_editor_property('lod_groups'))
    asset.set_editor_property('lod_settings', policy)
    models = list(asset.get_editor_property('source_models'))
    for i, model in enumerate(models):
        model.set_editor_property('reduction_settings', groups[min(i, 2)].get_editor_property('reduction_settings'))
    asset.set_editor_property('source_models', models)
