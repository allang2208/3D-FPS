"""Retarget Epic Kwang full-body source takes into new Jason-only packages."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT/'SourceAssets/ThirdPersonSwordKwang20261006'
DEST = '/Game/Characters/JasonPlayer20261003/KwangSword20261006'
lib = u.EditorAssetLibrary
assets = u.AssetToolsHelpers.get_asset_tools()
data = json.loads((OUT/'original-poses.json').read_text())
cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
source = u.load_asset(data['mesh'])
target = u.load_asset(cfg['body_mesh'])
names = data['names']

def save(asset):
    if not lib.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save '+asset.get_path_name())

def create(name, cls, factory):
    path = DEST+'/Rig/'+name
    if lib.does_asset_exist(path):
        return u.load_asset(path)
    return assets.create_asset(name, DEST+'/Rig', cls, factory)

ik = create('IK_Kwang_Sword', u.IKRigDefinition, u.IKRigDefinitionFactory())
c = u.IKRigController.get_controller(ik)
c.set_skeletal_mesh(source)
c.set_retarget_root('pelvis')
spines = [n for n in names if n.startswith('spine_') and n[-2:].isdigit()]
necks = [n for n in names if n.startswith('neck_') and n[-2:].isdigit()]
chains = {'Spine':(spines[0],spines[-1]), 'Neck':(necks[0],necks[-1]), 'Head':('head','head')}
for side in ('l','r'):
    for label,start,end in [('Clavicle','clavicle','clavicle'),('Arm','upperarm','hand'),('Leg','thigh','foot'),('Toe','ball','ball')]:
        chains[label+'_'+side] = (start+'_'+side,end+'_'+side)
    for digit in ('thumb','index','middle','ring','pinky'):
        chains[digit+'_'+side] = (digit+'_01_'+side,digit+'_03_'+side)
for label,(start,end) in chains.items():
    c.add_retarget_chain(label,start,end,'')
save(ik)
rtg = create('RTG_Kwang_Jason_Sword',u.IKRetargeter,u.IKRetargetFactory())
c = u.IKRetargeterController.get_controller(rtg)
c.set_ik_rig(u.RetargetSourceOrTarget.SOURCE,ik)
c.set_ik_rig(u.RetargetSourceOrTarget.TARGET,u.load_asset('/Game/Characters/JasonPlayer20261003/SwordFullBody20261005/Rig/IK_Jason_Sword'))
c.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE,source)
c.set_preview_mesh(u.RetargetSourceOrTarget.TARGET,target)
c.add_default_ops()
c.auto_map_chains(u.AutoMapChainType.EXACT,True)
pose = c.create_retarget_pose('Jason_Kwang_Aligned',u.RetargetSourceOrTarget.TARGET)
c.set_current_retarget_pose(pose,u.RetargetSourceOrTarget.TARGET)
c.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET)
save(rtg)
selected = [v['asset'] for v in data['clips'].values()]
inputs = u.IKRetargetBatchOperationInputs()
inputs.assets_to_retarget = [lib.find_asset_data(p) for p in selected]
inputs.source_mesh = source
inputs.target_mesh = target
inputs.ik_retarget_asset = rtg
inputs.prefix = 'J_Kwang_'
inputs.target_path = DEST+'/Retargeted'
inputs.include_referenced_assets = False
inputs.overwrite_existing_files = False
outputs = u.IKRetargetBatchOperation.run_batch_retarget(inputs)
options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = target
options.evaluation_type = u.AnimDataEvalType.SOURCE
ref = target.skeleton.get_reference_pose()
names = [str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
component = u.new_object(u.SkeletalMeshComponent)
component.set_skeletal_mesh_asset(target)
parents = [names.index(str(component.get_parent_bone(n))) if str(component.get_parent_bone(n)) in names else -1 for n in names]

def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]

clips = {}
for entry in outputs:
    clip = entry.get_asset()
    if not isinstance(clip,u.AnimSequence):
        continue
    clip.set_preview_skeletal_mesh(target)
    save(clip)
    duration = clip.get_play_length()
    count = round(duration*60)+1
    frames = []
    for i in range(count):
        p = u.AnimPoseExtensions.get_anim_pose_at_time(clip,duration*i/(count-1),options)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.LOCAL)) for n in names])
    clips[clip.get_name().removeprefix('J_Kwang_')] = dict(asset=clip.get_path_name(),duration=duration,frames=frames)
result = dict(mesh=target.get_path_name(),names=names,parents=parents,
              reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names],clips=clips)
(OUT/'retargeted-poses.json').write_text(json.dumps(result,separators=(',',':')))
print('KWANG_RETARGETED_SAVED '+json.dumps({n:c['asset'] for n,c in clips.items()}))

# Blade geometry is read through GeometryScript by read_kwang_blade_geometry.py.
# UE's FBX mesh exporter requires a render MeshObject even in a commandlet.
