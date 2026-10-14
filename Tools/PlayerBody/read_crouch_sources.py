"""Read the staged crouch cycles/legs; no gameplay, rendering or asset saves."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/ThirdPersonCrouch20261005'
data = json.loads((OUT/'donors.json').read_text(encoding='utf-8'))
u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/Game/Characters/UEFN_Mannequin'], True)
mesh = u.load_asset('/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin')
options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = mesh
bones = ['root','pelvis','spine_01']+[b+'_'+s for s in ('l','r') for b in ('thigh','calf','foot','ball')]
def pack(t):
    v, q = t.translation,t.rotation
    return {'p':[v.x,v.y,v.z],'q':[q.x,q.y,q.z,q.w]}
result = {'mesh':mesh.get_path_name(),'clips':{}}
for name,path in data['clips'].items():
    clip = u.load_asset(path)
    if not isinstance(clip,u.AnimSequence):
        raise RuntimeError('Missing crouch donor: '+path)
    length=clip.get_play_length()
    row = {'path':path,'length':length,
           'markers':[{'name':str(m.marker_name),'time':m.time} for m in u.AnimationLibrary.get_animation_sync_markers(clip)],
           'samples':[]}
    for i in range(65):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,length*i/64,options)
        row['samples'].append({'t':length*i/64,'bones':{b:pack(u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in bones}})
    result['clips'][name]=row
(OUT/'source-poses.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('CROUCH_SOURCES_READ '+json.dumps({n:{'length':r['length'],'markers':r['markers']} for n,r in result['clips'].items()}))
