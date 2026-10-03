"""Export installed 715 bind meshes and motion samples as RSH-12 authoring inputs.

No preview, gameplay, acceptance test, or source asset modification.
"""
import unreal as u, json, math
from pathlib import Path
O=Path(__file__).parent
E=u.EditorAssetLibrary
families={}
single='/Game/Weapons/DanWesson715'
clips={k:single+'/Upgrade20260914/Animations/A_DW715_'+k for k in ('idle','aim','fire','aim_fire','equip_charge','inspect')}
clips['quickcombat']=single+'/QuickCombat20260918/Animations/A_DW715_quickcombat'
clips['sprint']='/Game/Weapons/PistolLocomotion20260914/DW715/Animations/A_DW715_sprint'
for start in range(5):
    for count in range(1,6-start):
        kind=f'single_{start}_{count}'
        clips[kind]=single+('/PalmClearance20260915' if start==0 else '/LeftRecovery20260914')+'/Animations/A_DW715_'+kind
families['single']={'mesh':single+'/Chrome20260914/SK_DW715_Manny','clips':clips}
for side in ('r','l'):
    base=f'/Game/Weapons/PistolDualWield20260914/DW715/{side}'
    stem=f'Dual_DW715_{side}'
    cc={k:base+'/NaturalAimV3/Animations/A_'+stem+'_'+k for k in ('idle','fire','equip')}
    cc['sprint']=base+'/SprintSmoothV5/Animations/A_'+stem+'_sprint'
    for start in range(5):
        for count in range(1,6-start):
            kind=f'single_{start}_{count}';cc[kind]=base+'/RevolverReloadFlickV6/Animations/A_'+stem+'_'+kind
    for kind in ('quickcombat','quickcombat_left'):
        cc[kind]=f'/Game/Weapons/DualPistolQuickCombat20260920/SpinRecoveryV5/DW715/{side}/Animations/A_{stem}_{kind}'
    families[side]={'mesh':base+'/SK_'+stem,'clips':cc}

def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]

for family,spec in families.items():
    out=O/'Donor'/family;out.mkdir(parents=True,exist_ok=True)
    mesh=u.load_asset(spec['mesh'])
    if not mesh:raise RuntimeError('Missing installed donor '+spec['mesh'])
    dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read donor binding')
    _,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
    component=u.SkeletalMeshComponent();component.set_skeletal_mesh_asset(mesh)
    names=[str(b.name) for b in bones]
    parents={n:str(component.get_parent_bone(n)) for n in names}
    side='l' if family in ('single','l') else 'r'
    sampled=[n for n in names if n.startswith('WPN_') or n.endswith('_'+side)]
    data=dict(mesh=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),parents=parents,
        materials=[dict(slot=str(m.material_slot_name),name=m.material_interface.get_name(),asset=m.material_interface.get_path_name()) for m in mesh.materials if m.material_interface],
        rest={str(b.name):pack(b.world_transform) for b in bones},clips={})
    task=u.AssetExportTask();task.object=mesh;task.filename=str(out/'SK_DW715_Donor.fbx');task.automated=True;task.prompt=False
    task.exporter=u.SkeletalMeshExporterFBX();task.options=u.FbxExportOption();task.options.export_morph_targets=False
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Donor bind export failed')
    options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE;options.optional_skeletal_mesh=mesh;options.should_retarget=False
    for kind,path in spec['clips'].items():
        clip=u.load_asset(path)
        if not clip:raise RuntimeError('Missing installed donor '+path)
        duration=clip.get_play_length();steps=max(1,round(duration*60))
        rows=[]
        for i in range(steps+1):
            t=duration*i/steps;pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options)
            rows.append(dict(time=t,local={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in sampled},
                world={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in sampled}))
        data['clips'][kind]=dict(asset=clip.get_path_name(),duration=duration,samples=rows)
        print('RSH12_DONOR_INPUT',family,kind,len(rows),flush=True)
    (out/'motion.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    print('RSH12_DONOR_FAMILY_SAVED',family,flush=True)
