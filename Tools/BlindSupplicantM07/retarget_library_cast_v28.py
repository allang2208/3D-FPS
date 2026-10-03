"""Retarget the actual Vexa left-hand cast, preserving its whole-body motion."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001/LibraryCastV28')
DEST = '/Game/Monsters/BlindSupplicantM07'
RIG, RAW = DEST+'/Rig/LibraryCastV28', DEST+'/AnimationsLibraryCastV28Raw'
VEXA = '/Game/Vefects/Easy_Impact_Frames/Demo/Stylized_Female_Character_Vexa'
LIB, TOOLS = u.EditorAssetLibrary,u.AssetToolsHelpers.get_asset_tools()
source = u.load_asset(VEXA+'/SK/SK_Vefects_Vexa')
target = u.load_asset(DEST+'/SK_M07_BodyMotionV18')
clip = u.load_asset(VEXA+'/Animations/SnappySpell_Vexa')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('M07_V28_PIE_PRESERVED')
if any(p.get_path_name().startswith((RIG,RAW)) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Unsaved V28 retarget edits preserved.')

# Vexa inserts two twist subdivisions in each arm segment. Each segment uses
# corresponding anatomical endpoints, rather than treating all seven bones
# as three OneToOne joints. Forearm chains precede upper arms so auto-alignment
# uses the elbow's outgoing segment, not the incoming upper-arm tangent.
chains = {'Spine':(('Base-HumanSpine1','Base-HumanRibcage'),('spine_01','spine_05')),
          'Neck':(('Base-HumanNeck','Base-HumanNeck'),('neck_01','neck_02')),
          'Head':(('Base-HumanHead','Base-HumanHead'),('head','head'))}
for title,upper,side in (('Left','L','l'),('Right','R','r')):
    prefix = 'Base-Human'+upper
    chains['Forearm'+title] = ((prefix+'Forearm1',prefix+'Palm'),('lowerarm_'+side,'hand_'+side))
    chains['UpperArm'+title] = ((prefix+'Upperarm1',prefix+'Forearm1'),('upperarm_'+side,'lowerarm_'+side))
    chains['Clavicle'+title] = ((prefix+'Collarbone',prefix+'Upperarm1'),('clavicle_'+side,'upperarm_'+side))
    chains['Leg'+title] = ((prefix+'Thigh',prefix+'Foot'),('thigh_'+side,'foot_'+side))
    chains['Toes'+title] = ((prefix+'Foot',prefix+'Toes'),('foot_'+side,'ball_'+side))

def save(asset):
    if not LIB.save_loaded_asset(asset,False):
        raise RuntimeError('V28 native save failed: '+asset.get_path_name())
def create(name,cls,factory):
    return u.load_asset(RIG+'/'+name) or TOOLS.create_asset(name,RIG,cls,factory)
def ik(name,mesh,which,root):
    asset = create(name,u.IKRigDefinition,u.IKRigDefinitionFactory())
    ctl = u.IKRigController.get_controller(asset)
    ctl.set_skeletal_mesh(mesh)
    ctl.set_retarget_root(root)
    existing = {str(c.chain_name) for c in ctl.get_retarget_chains()}
    for name,pair in chains.items():
        if name not in existing:
            ctl.add_retarget_chain(name,*pair[which],'')
    save(asset)
    return asset
src = ik('IK_Vexa_CastSource',source,0,'Base-HumanPelvis')
dst = ik('IK_M07_LibraryCast',target,1,'pelvis')
rtg = create('RTG_Vexa_M07_CastV28',u.IKRetargeter,u.IKRetargetFactory())
ctl = u.IKRetargeterController.get_controller(rtg)
ctl.set_ik_rig(u.RetargetSourceOrTarget.SOURCE,src)
ctl.set_ik_rig(u.RetargetSourceOrTarget.TARGET,dst)
ctl.set_preview_mesh(u.RetargetSourceOrTarget.SOURCE,source)
ctl.set_preview_mesh(u.RetargetSourceOrTarget.TARGET,target)
if ctl.get_num_retarget_ops() == 0:
    ctl.add_default_ops()
ctl.auto_map_chains(u.AutoMapChainType.EXACT,True)
for i in range(ctl.get_num_retarget_ops()):
    op = ctl.get_op_controller(i)
    if isinstance(op,u.IKRetargetRootMotionController):
        ctl.set_retarget_op_enabled(i,False)
    if isinstance(op,u.IKRetargetFKChainsController):
        settings = op.get_settings()
        rows = list(settings.chains_to_retarget)
        for row in rows:
            row.rotation_mode = (u.FKChainRotationMode.ONE_TO_ONE if str(row.target_chain_name).startswith(('Leg','Toes'))
                                 else u.FKChainRotationMode.INTERPOLATED)
        settings.chains_to_retarget = rows
        op.set_settings(settings)
pose_name = ctl.create_retarget_pose('M07_VexaCastAligned',u.RetargetSourceOrTarget.TARGET)
ctl.set_current_retarget_pose(pose_name,u.RetargetSourceOrTarget.TARGET)
ctl.auto_align_all_bones(u.RetargetSourceOrTarget.TARGET)
save(rtg)
params = u.IKRetargetBatchOperationInputs()
params.assets_to_retarget = [LIB.find_asset_data(clip.get_path_name())]
params.source_mesh,params.target_mesh,params.ik_retarget_asset = source,target,rtg
params.search,params.replace = clip.get_name(),'A_M07_LibraryRaw_SnappySpell'
params.target_path = RAW
params.include_referenced_assets,params.overwrite_existing_files = False,True
results = u.IKRetargetBatchOperation.run_batch_retarget(params)
result = next((r.get_asset() for r in results if isinstance(r.get_asset(),u.AnimSequence)),None)
if not result:
    raise RuntimeError('V28 native cast not produced.')
result.set_preview_skeletal_mesh(target)
result.set_editor_property('enable_root_motion',False)
result.set_editor_property('force_root_lock',False)
save(result)
component = u.new_object(u.SkeletalMeshComponent)
component.set_skeletal_mesh_asset(target)
bones = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
options = u.AnimPoseEvaluationOptions()
options.evaluation_type = u.AnimDataEvalType.RAW
options.optional_skeletal_mesh = target
def transform(t):
    return dict(translation_cm=[t.translation.x,t.translation.y,t.translation.z],
                rotation_xyzw=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w])
frames = []
for i in range(round(result.get_play_length()*60)+1):
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(result,i/60.,options)
    frames.append({b:transform(u.AnimPoseExtensions.get_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in bones})
reference = {b:transform(u.AnimPoseExtensions.get_ref_bone_pose(pose,b,u.AnimPoseSpaces.WORLD)) for b in bones}
cache = ROOT/'native_pose_v28.json'
cache.write_text(json.dumps(dict(reference=reference,frames=frames,fps=60)),encoding='utf-8')
report = dict(source=clip.get_path_name(),source_mesh=source.get_path_name(),target_mesh=target.get_path_name(),
    raw_asset=result.get_path_name(),retargeter=rtg.get_path_name(),pose_cache=str(cache),
    duration_seconds=result.get_play_length(),fps=60,chains=chains,
    root_policy='PelvisRetarget_NoGroundRootCopy',method='Native UE segmented anatomical endpoint FK; full body cast',
    tested=False,rendered=False,formal_blueprint_changed=False)
(ROOT/'native_cast_v28.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('M07_V28_NATIVE_CAST_SAVED '+str(ROOT/'native_cast_v28.json'))
