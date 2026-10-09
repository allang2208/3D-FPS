"""Read current UE reload assets; no project asset changes or gameplay."""
import unreal as u,json,hashlib,math
from pathlib import Path
O=Path(__file__).parent/'Diagnostics';P=O.parents[2];O.mkdir(parents=True,exist_ok=True)
D='/Game/Weapons/Super90/Speedloader20261007'
mesh=u.load_asset('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7')
component=u.SkeletalMeshComponent();component.set_skeletal_mesh_asset(mesh)
names=[str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
def pack(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh;options.should_retarget=False
manifest=json.loads((P/'SourceAssets/Super90ContactR9_20261008/authoring.json').read_text())
out={'clips':{},'meshes':{},'profiles':{},'framing':{},'assets_changed':False}
for item in manifest['clips']:
    name=item['name'];clip=u.load_asset(D+'/Animations/'+name)
    if not clip:raise RuntimeError(name)
    sourcehash=u.EditorAssetLibrary.get_metadata_tag(clip,'Super90SourceSHA256')
    filehash=hashlib.sha256(Path(item['file']).read_bytes()).hexdigest()
    options.evaluation_type=u.AnimDataEvalType.COMPRESSED
    frames=range(round(clip.get_play_length()*60)+1) if item['count'] in (0,1,7) else sorted({0,74,87,90,round((clip.get_play_length())*60)})
    rows=[];max_error=0.
    for f in frames:
        options.evaluation_type=u.AnimDataEvalType.COMPRESSED
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,f/60.,options)
        row={'frame':f,'local':[pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names]}
        rows.append(row)
        if f%10==0 or f==frames[-1]:
            options.evaluation_type=u.AnimDataEvalType.SOURCE
            raw=u.AnimPoseExtensions.get_anim_pose_at_time(clip,f/60.,options)
            for n in ('hand_l','hand_r','WPN_root','WPN_Shell','WPN_SOCKET_Magazine'):
                a=u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)
                b=u.AnimPoseExtensions.get_bone_pose(raw,n,u.AnimPoseSpaces.WORLD)
                max_error=max(max_error,(a.translation-b.translation).length())
    out['clips'][name]={'length':clip.get_play_length(),'source_hash_matches':sourcehash==filehash,
      'revision':u.EditorAssetLibrary.get_metadata_tag(clip,'Super90SpeedloaderSource'),
      'source_compressed_position_error_ue':max_error,'rows':rows}
    print('READ_SAVED_CLIP',name,flush=True)
for key,asset in [('M4','/Game/Weapons/M4ContactImpactFinal/A_AKM_idle'),('Super90','/Game/Weapons/Super90/Cransh20261006/Animations/A_Super90_idle')]:
    frame_options=u.AnimPoseEvaluationOptions();frame_options.should_retarget=False
    frame_options.evaluation_type=u.AnimDataEvalType.COMPRESSED
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(u.load_asset(asset),0.,frame_options)
    out['framing'][key]={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in ('hand_r','WPN_root','WPN_RearSight','WPN_FrontSight')}
out['names']=names
(O/'saved_assets.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
for key,path,exporter in [('guide',D+'/SM_Super90_LoaderGuide',u.StaticMeshExporterFBX),('props',D+'/SK_Super90_LoaderProps',u.SkeletalMeshExporterFBX),('weapon','/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7',u.SkeletalMeshExporterFBX)]:
    obj=u.load_asset(path);task=u.AssetExportTask();task.object=obj;task.filename=str(O/(key+'.fbx'))
    task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=exporter()
    opts=u.FbxExportOption();opts.ascii=False;opts.level_of_detail=False;opts.collision=False;task.options=opts
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export '+path)
    out['meshes'][key]={'path':path,'source_files':list(obj.get_editor_property('asset_import_data').extract_filenames())}
for family in ('vertical','tactical_vertical','canted','prism','angled'):
    path='/Game/Weapons/Super90/Foregrips20261007/Meshes/SM_Super90_'+family
    task=u.AssetExportTask();task.object=u.load_asset(path);task.filename=str(O/('foregrip_'+family+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.StaticMeshExporterFBX()
    opts=u.FbxExportOption();opts.ascii=False;opts.level_of_detail=False;opts.collision=False;task.options=opts
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export '+path)
for family in ('vertical','canted','prism','angled'):
    profile=u.load_asset('/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_'+family)
    entries=[]
    for c in profile.get_editor_property('clips'):
        b=c.get_editor_property('base')
        if b and b.get_path_name().startswith(D+'/Animations/'):
            entries.append({'name':b.get_name(),'duration':c.get_editor_property('duration'),'retained':bool(c.get_editor_property('retained')),'tracks':len(c.get_editor_property('tracks'))})
    out['profiles'][family]=entries
(O/'saved_assets.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
print('SUPER90_R8_REVIEW_READ',len(out['clips']),flush=True)
