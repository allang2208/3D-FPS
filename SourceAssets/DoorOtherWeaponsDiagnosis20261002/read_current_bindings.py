"""User-requested read-only cross-weapon door-guard binding diagnosis."""
import hashlib
import json
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
PROJECT = Path(u.Paths.project_dir()).resolve()
config = json.loads((PROJECT / 'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
DONOR = '/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7.SK_M4_BareArmsV7'
output = dict(scope='Requested other-weapon whole-left-arm door-guard binding diagnosis',
              assets_changed=False, assets_saved=False, runtime_tested=False, rendered=False,
              donor_path=DONOR, sources={}, skipped=[], unavailable=[])


def xyz(v):
    return [v.x, v.y, v.z]


def transform(t):
    q = t.rotation
    return dict(position=xyz(t.translation), rotation_xyzw=[q.x, q.y, q.z, q.w], scale=xyz(t.scale3d))


sources = {p: v['rig_profile'] for p, v in config['profiles'].items()
           if v.get('rig_profile') not in ('Body', 'Traversal')
           and not v.get('rig_profile', '').endswith('_r')
           and '/LMG201/Production20260927/' not in p
           and '/DarkBow20260925/ArmsV4/' not in p}
sources[DONOR] = 'CanonicalM4'
for path, profile in sources.items():
    mesh = u.load_asset(path)
    if mesh is None:
        output['unavailable'].append(dict(profile=profile, path=path, reason='Asset unavailable'))
        continue
    dm, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        output['unavailable'].append(dict(profile=profile, path=path, reason='Native source could not be read'))
        continue
    _, bones = u.GeometryScript_BoneWeights.get_all_bones_info(dm)
    source_file = PROJECT / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
    output['sources'][path] = dict(profile=profile, path=path,
        source_sha256=hashlib.sha256(source_file.read_bytes()).hexdigest(), skeleton=mesh.skeleton.get_path_name(),
        bones={str(b.name): dict(index=b.index, parent=b.parent_index,
            local=transform(b.local_transform), component=transform(b.world_transform)) for b in bones})
    u.log('DOOR_OTHER_WEAPON_BINDING_READ ' + profile + ' ' + path)
(HERE / 'current-bindings.json').write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
u.log('DOOR_OTHER_WEAPON_CURRENT_BINDINGS_READ ' + str(len(output['sources'])))
