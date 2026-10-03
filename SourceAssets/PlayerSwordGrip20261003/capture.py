"""Read the accepted sword hold and native hand binds for grip authoring only."""
import json
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME')
R = Path(__file__).resolve().parent
cfg = json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))

def transform(t):
    return dict(p=[t.translation.x,t.translation.y,t.translation.z],
                q=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],
                s=[t.scale3d.x,t.scale3d.y,t.scale3d.z])

def bones(path):
    asset = u.load_asset(path)
    dm,status = u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError(path)
    _,info = u.GeometryScript_BoneWeights.get_all_bones_info(dm)
    return asset,dict(path=path,bones=[dict(name=str(b.name),parent=b.parent_index,
                                         **transform(b.world_transform)) for b in info])

body,target = bones(cfg['body_mesh'])
_,mount = bones(cfg['weapon_pose_reference_mesh'])
source,rig = bones('/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny')
clip = u.load_asset('/Game/Weapons/AzureRunesword20260913/A_RuneSword_Idle')
opts = u.AnimPoseEvaluationOptions()
opts.optional_skeletal_mesh=source
opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip,0.,opts)
sample = {b['name']:transform(u.AnimPoseExtensions.get_bone_pose(pose,b['name'],u.AnimPoseSpaces.WORLD)) for b in rig['bones']}
(R/'inputs.json').write_text(json.dumps(dict(body=target,mount=mount,source=rig,
    source_clip=clip.get_path_name(),pose=sample,body_idle=cfg['clips']['Unarmed.Idle']),indent=2))
print('SWORD_HAND_INPUTS_SAVED', 'PIE',len(u.EditorLevelLibrary.get_pie_worlds(False)),flush=True)
