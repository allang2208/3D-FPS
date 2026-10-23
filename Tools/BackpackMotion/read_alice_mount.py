"""Capture the exact current ALICE attachment in the native reference pose."""
import json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BackpackMotion20261022';R.mkdir(exist_ok=True)
cfg=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
settings=cfg['outfits']['ue_portable_backpack'];mesh=u.load_asset(cfg['body_mesh'])
dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
_,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
spine=next(b.world_transform for b in bones if str(b.name)==settings['attach_bone'])
rot=settings['attach_rotation'];mount=u.Transform(location=u.Vector(*settings['attach_location']),rotation=u.Rotator(pitch=rot[0],yaw=rot[1],roll=rot[2]),scale=u.Vector(*settings['attach_scale']))
source=json.loads((P/'SourceAssets/BackpacksReview20261021/alice_authored.json').read_text())
vec=lambda v:[v.x,v.y,v.z]
positions=[vec(spine.transform_location(mount.transform_location(u.Vector(*v)))) for v in source['positions']]
data={'settings':settings,'positions':positions,'reference_spine':str(spine),'body':cfg['body_mesh']}
(R/'alice_mount_before.json').write_text(json.dumps(data,separators=(',',':')))
print('ALICE_MOUNT_CAPTURED',flush=True)
