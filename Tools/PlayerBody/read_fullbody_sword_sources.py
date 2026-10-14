"""Read local full-body sword candidates and head/body bind data; save no assets."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/ThirdPersonSwordLibrary20261005'
OUT.mkdir(parents=True, exist_ok=True)
cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
def path(obj): return obj.get_path_name() if obj else None
def tf(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return {'p':[p.x,p.y,p.z], 'q':[q.x,q.y,q.z,q.w], 's':[s.x,s.y,s.z]}

base='/Game/Vefects/Easy_Impact_Frames/Demo/Stylized_Female_Character_Vexa'
u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([base], True)
mesh=u.load_asset(base+'/SK/SK_Vefects_Vexa')
options=u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh=mesh
result={'candidates':{},'reference':{}}
for name in ('SwordAttack_Vexa','SwordSlash_Vexa'):
    clip=u.load_asset(base+'/Animations/'+name)
    if not clip: continue
    row={'asset':path(clip),'mesh':path(mesh),'skeleton':path(clip.get_editor_property('skeleton')),
         'length':clip.get_play_length(),'samples':[]}
    for i in range(33):
        t=clip.get_play_length()*i/32
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options)
        names=[str(b) for b in u.AnimPoseExtensions.get_bone_names(pose)]
        if i==0:row['bones']=names
        selected=names
        row['samples'].append({'t':t,'bones':{b:tf(u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in selected}})
    result['candidates'][name]=row

for key,p in [('body',cfg['body_mesh']),('head',cfg['heads'][cfg['default_head']]['mesh'])]:
    asset=u.load_asset(p)
    if not asset:continue
    pose=asset.skeleton.get_reference_pose()
    component=u.new_object(u.SkeletalMeshComponent)
    component.set_skeletal_mesh_asset(asset)
    names=[str(b) for b in u.AnimPoseExtensions.get_bone_names(pose)]
    result['reference'][key]={'asset':path(asset),'skeleton':path(asset.skeleton),'bones':names,
        'post_process':str(asset.get_editor_property('post_process_anim_blueprint')),
        'parents':{b:str(component.get_parent_bone(b)) for b in names},
        'local':{b:tf(u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.LOCAL)) for b in names},
        'world':{b:tf(u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in names}}
(OUT/'sources.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('FULLBODY_SWORD_READ '+json.dumps({k:{'length':v['length'],'skeleton':v['skeleton'],'bone_count':len(v['bones'])} for k,v in result['candidates'].items()}))
