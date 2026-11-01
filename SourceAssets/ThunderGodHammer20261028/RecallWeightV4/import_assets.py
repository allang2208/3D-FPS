"""Save the two recall clips and derive authoritative catch frames from UE poses."""
import unreal as u,json,math,shutil,hashlib,datetime
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2];D='/Game/Weapons/ThunderGodHammer20261028/RecallCatchV2'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
motion=json.loads((P/'motion.json').read_text(encoding='utf-8'))
receipt={'complete':False,'saved':[],'runtime_tested':False,'preview_rendered':False}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
record();backup=P/('BeforeImport-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir();previous=[]
files=[R/'Content/Weapons/ThunderGodHammer20261028/RecallCatchV2'/(n+'.uasset') for n in motion['clips']]
files.append(R/'Source/FPSGAME/Production/ThunderHammerCatchFrames.h')
for file in files:
    if file.exists():shutil.copy2(file,backup/file.name);previous.append({'file':str(file),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
(backup/'manifest.json').write_text(json.dumps(previous,indent=2),encoding='utf-8')
arms=u.load_asset('/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
A=u.AssetToolsHelpers.get_asset_tools()
for name in motion['clips']:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=arms.get_editor_property('skeleton')
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',240)
    task=u.AssetImportTask();task.filename=str(P/'Export'/(name+'.fbx'));task.destination_path=D;task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True;task.options=opt
    A.import_asset_tasks([task]);clip=u.load_asset(D+'/'+name)
    if not clip:raise RuntimeError('Import failed '+name)
    clip.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));clip.set_editor_property('rate_scale',1.)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Finalize failed '+name)
    u.EditorAssetLibrary.set_metadata_tag(clip,'ThunderRecallRevision','RecallWeightV4: relaxed left arm, 17.4cm loaded compression, quick grasp and braced recovery')
    if not u.EditorLoadingAndSavingUtils.save_packages([clip.get_outermost()],False):raise RuntimeError('Save failed '+name)
    receipt['saved'].append(clip.get_path_name());record()
# This is production contact data, sampled from the imported animation rather
# than inferred from Blender axes. It drives remote authority without an arm mesh.
opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.SOURCE;opt.optional_skeletal_mesh=arms
clip=u.load_asset(D+'/A_ThunderHammer_Catch_V2')
mount=json.loads((R/'Content/ColdSteelData/thunder-god-hammer-modules.json').read_text(encoding='utf-8'))['bone_mount']
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def rotate(q,v):
    tmp=[2*x for x in cross(q[:3],v)];c=cross(q[:3],tmp)
    return [v[i]+q[3]*tmp[i]+c[i] for i in range(3)]
def mul(a,b):
    c=cross(a[:3],b[:3]);return [a[3]*b[i]+b[3]*a[i]+c[i] for i in range(3)]+[a[3]*b[3]-sum(a[i]*b[i] for i in range(3))]
yaw=[0,0,math.sqrt(.5),math.sqrt(.5)];frames=[]
for i in range(31):
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,i*.02,opt)
    transform=u.AnimPoseExtensions.get_bone_pose(pose,'WPN_root',u.AnimPoseSpaces.WORLD)
    v=rotate(mount['rotation_xyzw'],[0,0,70*mount['scale'][2]])
    v=[(v[j]+mount['location_cm'][j])*[transform.scale3d.x,transform.scale3d.y,transform.scale3d.z][j] for j in range(3)]
    q=[transform.rotation.x,transform.rotation.y,transform.rotation.z,transform.rotation.w];v=rotate(q,v)
    v=rotate(yaw,[v[j]+[transform.translation.x,transform.translation.y,transform.translation.z][j] for j in range(3)])
    q=mul(mul(yaw,q),mount['rotation_xyzw']);frames.append({'position_cm':v,'rotation_xyzw':q})
header='#pragma once\n#include "CoreMinimal.h"\n// Imported RecallWeightV4 palm-load motion; centre at shaft Z=70 cm.\nnamespace ThunderHammerThrow {\ninline constexpr float CatchFrameStepV4=.02f;\ninline const FTransform CatchFramesV4[]={\n'
for frame in frames:header+='    FTransform(FQuat('+','.join(format(x,'.12f') for x in frame['rotation_xyzw'])+'),FVector('+','.join(format(x,'.9f') for x in frame['position_cm'])+')),\n'
header+='};\n}\n';(R/'Source/FPSGAME/Production/ThunderHammerCatchFrames.h').write_text(header,encoding='utf-8')
receipt.update(complete=True,backup=str(backup),catch_frames=frames,source_fps=240,ready_loop_seconds=1.)
record();print('THUNDER_RECALL_WEIGHT_V4_SAVED',flush=True)
