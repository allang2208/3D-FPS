"""Read loaded reference frames for the requested M16 wrist diagnosis only."""
import hashlib
import json
from pathlib import Path
import unreal as u

P = Path(u.Paths.project_dir()).resolve()
O = Path(__file__).parent
paths = {
    'M16Weapon': '/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny.SK_M16_Manny',
    'M16Bare': '/Game/Characters/ModularOutfit20260924/BarePalmV7/M16/SK_M16_BareArmsV7.SK_M16_BareArmsV7',
    'M4Bare': '/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7.SK_M4_BareArmsV7',
}
def xyz(v):
    return [v.x, v.y, v.z]
result = {'scope': 'requested read-only loaded asset diagnosis; no asset changes or gameplay test', 'rigs': {}}
for key, path in paths.items():
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing rig ' + path)
    dm, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
        asset, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read rig ' + path)
    _, bones = u.GeometryScript_BoneWeights.get_all_bones_info(dm)
    package = P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')
    result['rigs'][key] = {
        'path': path, 'skeleton': asset.skeleton.get_path_name(),
        'disk_sha256': hashlib.sha256(package.read_bytes()).hexdigest(),
        'bones': {str(b.name): {'index': b.index, 'parent': b.parent_index,
            'position': xyz(b.world_transform.translation),
            'axes': [xyz(b.world_transform.transform_location(v) - b.world_transform.translation)
                for v in (u.Vector(1, 0, 0), u.Vector(0, 1, 0), u.Vector(0, 0, 1))]}
            for b in bones},
    }
(O / 'current-rigs.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
u.log('M16_SPRINT_DOOR_CURRENT_RIGS_READ ' + str(len(result['rigs'])))
