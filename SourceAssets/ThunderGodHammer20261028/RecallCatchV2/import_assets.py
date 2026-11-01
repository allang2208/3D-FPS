"""Import the right-hand recall clips and publish their native weapon/contact frames."""
import unreal as u,json,math
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2];D='/Game/Weapons/ThunderGodHammer20261028/RecallCatchV2'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
A=u.AssetToolsHelpers.get_asset_tools();receipt={'complete':False,'saved':[],'runtime_tested':False}
source=json.loads((P/'motion.json').read_text(encoding='utf-8'))
arms=u.load_asset('/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for name in source['clips']:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
    opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=arms.get_editor_property('skeleton')
    opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',240)
    t=u.AssetImportTask();t.filename=str(P/'Export'/(name+'.fbx'));t.destination_path=D;t.destination_name=name
    t.automated=True;t.save=False;t.replace_existing=True;t.replace_existing_settings=True;t.options=opt
    A.import_asset_tasks([t]);anim=u.load_asset(D+'/'+name)
    if not anim:raise RuntimeError('Import failed '+name)
    anim.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'))
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(anim):raise RuntimeError('Cannot finalize '+name)
    if not u.EditorLoadingAndSavingUtils.save_packages([anim.get_outermost()],False):raise RuntimeError('Save failed '+name)
    receipt['saved'].append(anim.get_path_name());(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
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
    t=u.AnimPoseExtensions.get_bone_pose(pose,'WPN_root',u.AnimPoseSpaces.WORLD)
    v=rotate(mount['rotation_xyzw'],[0,0,70*mount['scale'][2]])
    v=[(v[j]+mount['location_cm'][j])*[t.scale3d.x,t.scale3d.y,t.scale3d.z][j] for j in range(3)]
    q=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w];v=rotate(q,v)
    v=rotate(yaw,[v[j]+[t.translation.x,t.translation.y,t.translation.z][j] for j in range(3)])
    q=mul(mul(yaw,q),mount['rotation_xyzw']);frames.append({'position_cm':v,'rotation_xyzw':q})
header='#pragma once\n#include "CoreMinimal.h"\n// Imported RecallCatchV2 WPN_root and module mount; centre at shaft Z=70 cm.\nnamespace ThunderHammerThrow {\ninline constexpr float CatchFrameStep=.02f;\ninline const FTransform CatchFrames[]={\n'
for f in frames:header+='    FTransform(FQuat('+','.join(format(x,'.12f') for x in f['rotation_xyzw'])+'),FVector('+','.join(format(x,'.9f') for x in f['position_cm'])+')),\n'
header+='};\n}\n';(R/'Source/FPSGAME/Production/ThunderHammerCatchFrames.h').write_text(header,encoding='utf-8')
receipt.update(complete=True,catch_frames=frames,source_fps=240);(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('THUNDER_RECALL_CATCH_SAVED')
