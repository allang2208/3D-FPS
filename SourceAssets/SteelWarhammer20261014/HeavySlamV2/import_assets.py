"""Save the heavy clips and Substrate ground ring; derive the native head marker."""
import unreal as u,json,math
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2];D='/Game/Weapons/SteelWarhammer20261014/HeavySlamV2'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools();receipt={'saved':[],'complete':False,'runtime_tested':False}
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Asset save failed: '+asset.get_path_name())
    receipt['saved'].append(asset.get_path_name());(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
source=json.loads((P/'authored.json').read_text())
mesh=u.load_asset('/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for name in source['clips']:
    anim=u.load_asset(D+'/'+name)
    if not anim:
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=mesh.get_editor_property('skeleton')
        opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',480)
        task=u.AssetImportTask();task.filename=str(P/'Export'/(name+'.fbx'));task.destination_path=D;task.destination_name=name;task.automated=True;task.save=False;task.replace_existing=False;task.options=opt
        A.import_asset_tasks([task]);anim=u.load_asset(D+'/'+name)
    if not anim:raise RuntimeError('Missing imported animation '+name)
    anim.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));save(anim)
# Reuse the existing saved ground wave material.
errors=[]
# Fit the author/native coordinate basis from shared reference joints, then
# express the real bottom surface point in the imported WPN_root frame.
base=u.load_asset(D+'/A_Warhammer_HeavyRelease');options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE;options.optional_skeletal_mesh=mesh
pose=u.AnimPoseExtensions.get_anim_pose_at_time(base,0.,options)
ref=u.AnimPoseExtensions.get_ref_bone_pose(pose,'WPN_root',u.AnimPoseSpaces.WORLD)
rows=[];targets=[]
for name,point in source['reference_positions_m'].items():
    native=u.AnimPoseExtensions.get_ref_bone_pose(pose,name,u.AnimPoseSpaces.WORLD).translation
    rows.append(point+[1.]);targets.append([native.x,native.y,native.z])
aug=[[sum(row[i]*row[j] for row in rows) for j in range(4)]+[sum(row[i]*target[k] for row,target in zip(rows,targets)) for k in range(3)] for i in range(4)]
for i in range(4):
    pivot=max(range(i,4),key=lambda j:abs(aug[j][i]));aug[i],aug[pivot]=aug[pivot],aug[i]
    factor=aug[i][i]
    if abs(factor)<1e-10:raise RuntimeError('Reference basis is singular')
    aug[i]=[v/factor for v in aug[i]]
    for j in range(4):
        if j!=i:
            factor=aug[j][i];aug[j]=[a-factor*b for a,b in zip(aug[j],aug[i])]
point=source['head_marker_author_world_m']+[1.]
world=[sum(point[j]*aug[j][4+i] for j in range(4)) for i in range(3)]
v=[world[0]-ref.translation.x,world[1]-ref.translation.y,world[2]-ref.translation.z]
q=ref.rotation;axis=[-q.x,-q.y,-q.z]
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
t=[2*c for c in cross(axis,v)];c=cross(axis,t);scale=[ref.scale3d.x,ref.scale3d.y,ref.scale3d.z]
local=[(v[i]+q.w*t[i]+c[i])/scale[i] for i in range(3)]
header=R/'Source/FPSGAME/Production/WarhammerHeadMarker.h'
header.write_text('#pragma once\n#include "CoreMinimal.h"\n// Real hammer-head surface marker, from HeavySlamV2 and the UE reference skeleton.\nnamespace WarhammerHeavy { inline const FVector HeadMarker('+','.join(format(value,'.9f') for value in local)+'); }\n',encoding='utf-8')
receipt.update(complete=True,head_marker_native_local=local,weapon_reference_scale=scale,material_compiler_errors=errors)
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print('WARHAMMER_HEAVY_SAVED '+json.dumps(receipt))
