"""Read the current 201 idles, reference skeleton and body export (read only)."""
import unreal as u, json, hashlib
from pathlib import Path

O = Path(__file__).parent
(O / 'Inputs').mkdir(parents=True, exist_ok=True)
P = O.parents[2]
BODY = '/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'


def tr(t):
    return [*t.translation.to_tuple(), t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w, *t.scale3d.to_tuple()]


def sha(path):
    return hashlib.sha256((P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')).read_bytes()).hexdigest()


mesh = u.load_asset(BODY)
dm, status = u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
_, rows = u.GeometryScript_BoneWeights.get_all_bones_info(dm)
rows = sorted(rows, key=lambda b: b.index)
names = [str(b.name) for b in rows]
result = {'mesh': {'asset': BODY, 'sha256': sha(BODY), 'names': names, 'parents': [b.parent_index for b in rows],
                   'rest': [tr(b.world_transform) for b in rows]}, 'clips': {}}
ex = u.AssetExportTask()
ex.object = mesh
ex.filename = str(O / 'Inputs' / 'body_current.fbx')
ex.automated = True
ex.prompt = False
ex.replace_identical = True
ex.options = u.FbxExportOption()
ex.options.level_of_detail = False
ex.options.export_morph_targets = False
ex.options.bake_material_inputs = u.FbxMaterialBakeMode.DISABLED
if not u.Exporter.run_asset_export_task(ex):
    raise RuntimeError('Body export failed')
clips = {'201_idle': '/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_idle'}
for v in ('vertical', 'canted', 'prism', 'angled'):
    clips['201_%s_idle' % v] = '/Game/Weapons/LMG201/Accessories22/Animations/%s/A_LMG201_%s_idle' % (v, v)
opts = u.AnimPoseEvaluationOptions()
opts.optional_skeletal_mesh = mesh
opts.evaluation_type = u.AnimDataEvalType.SOURCE
for key, asset in clips.items():
    clip = u.load_asset(asset)
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, 0.0, opts)
    data = {'asset': asset, 'sha256': sha(asset), 'seconds': clip.get_play_length(),
            'metadata': {str(k): str(v) for k, v in u.EditorAssetLibrary.get_metadata_tag_values(clip).items()},
            'poses': [[tr(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.LOCAL)) for n in names]]}
    f = O / 'Inputs' / (key + '.json')
    f.write_text(json.dumps(data, separators=(',', ':')))
    result['clips'][key] = {'file': str(f), 'asset': asset, 'sha256': data['sha256'], 'metadata': data['metadata']}
    print('RELOAD44_READ', key, flush=True)
(O / 'inputs.json').write_text(json.dumps(result, indent=2))
print('RELOAD44_INPUTS_SAVED', flush=True)
