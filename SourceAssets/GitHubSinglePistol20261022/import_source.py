"""Import the selected GitHub donor to a new authoring-only folder."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/GitHubSinglePistol20261022'
DEST='/Game/Characters/JasonPlayer20261003/GitHubSinglePistol20261022/SourceV2'
lib=u.EditorAssetLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
def load_fbx(name,skeleton=None):
    target_name='A_'+name if skeleton else 'SK_GitHubPistol'
    object_path=DEST+'/'+target_name+'.'+target_name
    existing=u.load_asset(object_path) if lib.does_asset_exist(object_path) else None
    if existing:return existing
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION if skeleton else u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal=not bool(skeleton);options.import_mesh=not bool(skeleton)
    options.import_animations=bool(skeleton);options.import_materials=False;options.import_textures=False
    options.create_physics_asset=False
    if skeleton:options.skeleton=skeleton
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
    options.anim_sequence_import_data.set_editor_property('snap_to_closest_frame_boundary',True)
    task=u.AssetImportTask();task.filename=str(OUT/'Converted'/f'{name}.fbx')
    task.destination_path=DEST;task.destination_name=target_name
    task.automated=True;task.replace_existing=False;task.save=True;task.options=options;task.factory=u.FbxFactory()
    assets.import_asset_tasks([task])
    result=u.load_asset(object_path)
    if not result:raise RuntimeError('Import did not create '+target_name+' '+str(task.imported_object_paths))
    if isinstance(result,u.SkeletalMesh):
        if not result.skeleton:raise RuntimeError('Imported mesh has no skeleton')
        print('GITHUB_SKELETON_SAVE',result.skeleton.get_path_name(),flush=True)
        if not lib.save_loaded_asset(result.skeleton,False):raise RuntimeError('Cannot persist imported skeleton')
        if not lib.save_loaded_asset(result,False):raise RuntimeError('Cannot persist imported mesh')
    return result
mesh=load_fbx('RevolverAimIdle')
print('GITHUB_SOURCE_MESH',mesh.get_path_name(),mesh.get_class().get_name(),mesh.skeleton.get_path_name(),flush=True)
if not lib.save_loaded_asset(mesh.skeleton,False):raise RuntimeError('Skeleton save failed')
clips={}
for path in sorted((OUT/'Converted').glob('*.fbx')):
    clip=load_fbx(path.stem,mesh.skeleton)
    print('GITHUB_SOURCE_CLIP',clip.get_path_name(),clip.get_class().get_name(),flush=True)
    lib.set_metadata_tag(clip,'SourceRepository','https://github.com/ZenXChaos/ThirdPersonShooter-AnimationSets')
    lib.set_metadata_tag(clip,'SourceRevision','f19adc2ece4cab0f89c9236223abb97d4d2badea')
    if not lib.save_loaded_asset(clip,False):raise RuntimeError('Save '+clip.get_path_name())
    clips[path.stem]=dict(asset=clip.get_path_name(),duration=clip.get_play_length())
    (OUT/'import-receipt.json').write_text(json.dumps(dict(mesh=mesh.get_path_name(),clips=clips),indent=2),encoding='utf8')
    print('GITHUB_PISTOL_IMPORTED',path.stem,clip.get_play_length(),flush=True)
def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
def skeleton_data(m):
    pose=m.skeleton.get_reference_pose();names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(pose)]
    component=u.new_object(u.SkeletalMeshComponent);component.set_skeletal_mesh_asset(m)
    return dict(mesh=m.get_path_name(),names=names,
        parents=[names.index(str(component.get_parent_bone(n))) if str(component.get_parent_bone(n)) in names else -1 for n in names],
        reference=[pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
data=dict(source=skeleton_data(mesh),target=skeleton_data(u.load_asset(cfg['body_mesh'])),clips={})
opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=u.AnimDataEvalType.SOURCE
for name,entry in clips.items():
    clip=u.load_asset(entry['asset']);duration=clip.get_play_length();frames=[]
    for i in range(round(duration*30)+1):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,min(i/30,duration),opt)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in data['source']['names']])
    data['clips'][name]=dict(**entry,rate=30,frames=frames)
(OUT/'source-poses.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
print('GITHUB_PISTOL_SOURCE_READY',len(clips),flush=True)
