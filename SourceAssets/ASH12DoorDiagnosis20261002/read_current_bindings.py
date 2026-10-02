"""User-requested read-only binding diagnosis; no assets are changed or saved."""
import hashlib
import json
from pathlib import Path
import unreal as u

HERE = Path(__file__).resolve().parent
PROJECT = Path(u.Paths.project_dir()).resolve()
SOURCES = {
    'ASH12': '/Game/Weapons/ASH12/Surface20260919/SK_ASH12_Surface.SK_ASH12_Surface',
    'M4Donor': '/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7.SK_M4_BareArmsV7',
}


def xyz(v):
    return [v.x, v.y, v.z]


def transform(t):
    q = t.rotation
    return dict(position=xyz(t.translation), rotation_xyzw=[q.x, q.y, q.z, q.w],
                scale=xyz(t.scale3d))


output = dict(scope='Requested ASH12 left-arm binding and retarget diagnosis',
              assets_changed=False, assets_saved=False, runtime_tested=False, rendered=False, sources={})
for name, path in SOURCES.items():
    mesh = u.load_asset(path)
    if mesh is None:
        raise RuntimeError('Current binding input unavailable: ' + path)
    dm, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read current native source: ' + path)
    _, bones = u.GeometryScript_BoneWeights.get_all_bones_info(dm)
    source_file = PROJECT / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
    output['sources'][name] = dict(path=path,
        source_sha256=hashlib.sha256(source_file.read_bytes()).hexdigest(),
        skeleton=mesh.skeleton.get_path_name(),
        bones={str(b.name): dict(index=b.index, parent=b.parent_index,
            local=transform(b.local_transform), component=transform(b.world_transform)) for b in bones})
(HERE / 'current-bindings.json').write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
u.log('ASH12_DOOR_CURRENT_BINDINGS_READ ' + str(len(output['sources'])))
