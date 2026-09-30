"""Save native FP repairs, preserving the already-corrected SVD source fit."""
import sys
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME')
R = Path(__file__).resolve().parent
sys.path.insert(0, str(P / 'Tools/ModularOutfit'))
import garment_ue as g

DEST = '/Game/Characters/ModularOutfit20260924/CharcoalCameraRepair20260930'
B = u.GeometryScript_BoneWeights
E = u.EditorAssetLibrary


def main(start=0, end=21):
    sources = g.read(R / 'before.json')['sources']
    active = g.read(P / 'Content/ColdSteelData/modular_outfits.json')['items']['ue_field_sweater_charcoal']['rig_meshes']
    receipts = g.read(R / 'saved.json') if (R / 'saved.json').exists() else {}
    for profile in list(sources)[start:end]:
        source_path = sources[profile]
        paths = g.read(R / 'Before' / profile / 'paths.json')
        if active[profile] != source_path or g.digest(g.asset_file(source_path)) != paths['source_sha256']:
            raise RuntimeError('Source changed while authoring: ' + profile)
        if g.digest(g.asset_file(paths['skin'])) != paths['skin_sha256']:
            raise RuntimeError('Native arm source changed: ' + profile)
        if profile in receipts:
            if g.digest(g.asset_file(receipts[profile]['asset'])) != receipts[profile]['asset_sha256']:
                raise RuntimeError('Saved output changed: ' + profile)
            if profile != 'SVD' and g.digest(R / 'Authored' / (profile + '.json')) != receipts[profile]['author_sha256']:
                raise RuntimeError('Author data changed after saving: ' + profile)
            continue
        source = u.load_asset(source_path)
        binding = None
        if profile == 'SVD':
            dm, data = g.source_snapshot(source)
            contract = 'Preserve current SVD shoulder opening, all fitted vertices and native weights; update garment LOD policy only'
        else:
            data = g.read(R / 'Authored' / (profile + '.json'))
            binding = u.load_asset(paths['skin'])
            native, _ = g.source_snapshot(binding)
            _, bones = B.get_all_bones_info(native)
            bone_ids = {str(b.name): b.index for b in bones}
            vertices, normals, uvs, weights, triangles, lookup = [], [], [], [], [], {}
            for fi, face in enumerate(data['triangles']):
                row = []
                for ci, vi in enumerate(face):
                    normal, uv = data['normals'][fi][ci], data['uv'][fi][ci]
                    key = (vi, data['triangle_materials'][fi], *[round(v, 7) for v in normal + uv])
                    if key not in lookup:
                        lookup[key] = len(vertices)
                        vertices.append(u.Vector(*data['positions'][vi])); normals.append(u.Vector(*normal))
                        uvs.append(u.Vector2D(*uv)); weights.append(data['weights'][vi])
                    row.append(lookup[key])
                triangles.append(u.IntVector(*row))
            dm = u.DynamicMesh()
            u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,
                u.GeometryScriptSimpleMeshBuffers(vertices=vertices, normals=normals, uv0=uvs, triangles=triangles), 0, True)
            if dm.get_triangle_count() != len(triangles):
                raise RuntimeError('Rejected cloth triangles: ' + profile)
            B.copy_bones_from_mesh(native, dm); B.mesh_create_bone_weights(dm)
            for vi, values in enumerate(weights):
                _, ok = B.set_vertex_bone_weights(dm, vi, [u.GeometryScriptBoneWeight(bone_index=bone_ids[n], weight=w) for n, w in values.items()])
                if not ok:
                    raise RuntimeError('Native cloth weight assignment failed: ' + profile)
            for fi, material in enumerate(data['triangle_materials']):
                u.GeometryScript_Materials.set_triangle_material_id(dm, fi, material, True)
            contract = data['contract']
        destination = DEST + '/' + profile + '/SK_' + profile + '_Charcoal'
        folder = R / 'Saved' / profile
        receipt = g.save_candidate(dm, source, destination, folder, binding=binding)
        asset = u.load_asset(destination)
        asset.set_editor_property('physics_asset', None)
        E.set_metadata_tag(asset, 'SourceContract', contract)
        if not E.save_loaded_asset(asset, False):
            raise RuntimeError('Cannot save repaired cloth metadata: ' + profile)
        receipt.update(asset_sha256=g.digest(g.asset_file(destination)), source=source_path,
            source_sha256=paths['source_sha256'], native_skin=paths['skin'],
            native_skin_sha256=paths['skin_sha256'], runtime_tested=False,
            repair='LOD policy only; current SVD geometry preserved' if profile == 'SVD' else 'Native V7 paired sleeve shell and weights')
        if profile != 'SVD':
            receipt['author_sha256'] = g.digest(R / 'Authored' / (profile + '.json'))
        g.write(folder / 'saved.json', receipt)
        receipts[profile] = receipt
        g.write(R / 'saved.json', receipts)
        print('CHARCOAL_CAMERA_SAVED', profile, receipt['asset'], flush=True)
    print('CHARCOAL_CAMERA_BATCH_DONE', start, end, 'saved_total', len(receipts), flush=True)


if __name__ == '__main__':
    main()
