"""Read saved RSH geometry and sparse profiles for the requested mechanism diagnosis."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];out=O/'Before';out.mkdir(exist_ok=True)
def pack(t):return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
def export_profile(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError(path)
    clips=[]
    for c in a.get_editor_property('clips'):
        retained=c.get_editor_property('retained')
        clips.append(dict(base=c.get_editor_property('base').get_path_name(),duration=c.get_editor_property('duration'),retained=retained.get_path_name() if retained else None,
            tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in c.get_editor_property('tracks')]))
    data=dict(asset=a.get_path_name(),family=str(a.get_editor_property('family')),clips=clips)
    (out/(a.get_name()+'.json')).write_text(json.dumps(data,separators=(',',':')))
    return data
for side in ('single','r','l'):
    name='SK_RSH12_Manny' if side=='single' else 'SK_Dual_RSH12_'+side
    mesh=u.load_asset('/Game/Weapons/RSH12/Native71520261003/'+side+'/'+name)
    profile=export_profile('/Game/Weapons/RSH12/Native71520261003/Profiles/DA_RSH12_'+('' if side=='single' else side+'_')+'base')
    dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    _,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
    data=dict(rest={str(b.name):pack(b.world_transform) for b in bones},samples={})
    for c in profile['clips']:
        clip=u.load_asset(c['base']);kind=clip.get_name()
        if not kind.endswith(('idle','single_0_5','speed_0')):continue
        data['samples'][kind]={}
        for retarget in (False,True):
            options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.COMPRESSED;options.optional_skeletal_mesh=mesh;options.should_retarget=retarget
            rows=[]
            for t in (0.,c['duration']*.3,c['duration']*.6,c['duration']):
                pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options)
                rows.append(dict(time=t,local={str(b.name):pack(u.AnimPoseExtensions.get_bone_pose(pose,b.name,u.AnimPoseSpaces.LOCAL)) for b in bones}))
            data['samples'][kind][str(retarget)]=rows
    (out/(side+'_mesh.json')).write_text(json.dumps(data,separators=(',',':')))
    task=u.AssetExportTask();task.object=mesh;task.filename=str(out/(side+'.fbx'));task.automated=True;task.prompt=False
    task.exporter=u.SkeletalMeshExporterFBX();task.options=u.FbxExportOption();task.options.export_morph_targets=False
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed '+side)
    print('RSH_MECHANICAL_INPUT',side,flush=True)
for family in ('angled','vertical','canted','prism'):
    export_profile('/Game/Weapons/RSH12/Foregrips20261004/Profiles/DA_RSH12_'+family)
print('RSH_ACTIVE_MECHANICAL_INPUTS_SAVED',flush=True)
