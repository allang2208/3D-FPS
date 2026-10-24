"""The End FBX has its own pre-rotation/bind basis. Retarget on that basis."""
import json,runpy
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/GitHubSinglePistol20261022'
BASE='/Game/Characters/JasonPlayer20261003/GitHubSinglePistol20261022'
DEST=BASE+'/SourceEndBind'
lib=u.EditorAssetLibrary;assets=u.AssetToolsHelpers.get_asset_tools()
def load(name,skeleton=None,source_name='RevolverReloadEnd'):
    path=DEST+'/'+name+'.'+name
    if lib.does_asset_exist(path):return u.load_asset(path)
    o=u.FbxImportUI();o.automated_import_should_detect_type=False
    o.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION if skeleton else u.FBXImportType.FBXIT_SKELETAL_MESH
    o.import_as_skeletal=not bool(skeleton);o.import_mesh=not bool(skeleton);o.import_animations=bool(skeleton)
    o.import_materials=False;o.import_textures=False;o.create_physics_asset=False
    if skeleton:o.skeleton=skeleton
    o.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    o.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
    o.anim_sequence_import_data.set_editor_property('snap_to_closest_frame_boundary',True)
    t=u.AssetImportTask();t.filename=str(OUT/'Converted'/f'{source_name}.fbx');t.destination_path=DEST;t.destination_name=name
    t.automated=True;t.save=True;t.replace_existing=False;t.options=o;t.factory=u.FbxFactory();assets.import_asset_tasks([t])
    result=u.load_asset(path)
    if not result:raise RuntimeError('Missing '+path)
    if isinstance(result,u.SkeletalMesh):
        if not lib.save_loaded_asset(result.skeleton,False):raise RuntimeError('Skeleton save')
    if not lib.save_loaded_asset(result,False):raise RuntimeError('Asset save')
    return result
mesh=load('SK_GitHubEndBind');clip=load('A_RevolverReloadEnd',mesh.skeleton)
def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
ref=mesh.skeleton.get_reference_pose();names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
component=u.new_object(u.SkeletalMeshComponent);component.set_skeletal_mesh_asset(mesh)
source=dict(mesh=mesh.get_path_name(),names=names,
    parents=[names.index(str(component.get_parent_bone(n))) if str(component.get_parent_bone(n)) in names else -1 for n in names],
    reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names])
original=json.loads((OUT/'source-poses.json').read_text(encoding='utf8'))
data=dict(source=source,target=original['target'],clips={'RevolverReloadEnd':dict(asset=clip.get_path_name(),duration=clip.get_play_length())})
(OUT/'source-end-bind.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
runpy.run_path(str(OUT/'retarget_source.py'),init_globals={'RETARGET_INPUT':'source-end-bind.json','RETARGET_VARIANT':'EndBind_'})

# Crouch Init is the other take authored with the alternate local bone axes.
# Keep its own reference too rather than assuming a matching End bind.
DEST=BASE+'/SourceCrouchInitBind'
mesh=load('SK_GitHubCrouchInitBind',source_name='RevolverCrouchAimReloadInit')
clip=load('A_RevolverCrouchAimReloadInit',mesh.skeleton,'RevolverCrouchAimReloadInit')
ref=mesh.skeleton.get_reference_pose();names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(ref)]
component=u.new_object(u.SkeletalMeshComponent);component.set_skeletal_mesh_asset(mesh)
source=dict(mesh=mesh.get_path_name(),names=names,
    parents=[names.index(str(component.get_parent_bone(n))) if str(component.get_parent_bone(n)) in names else -1 for n in names],
    reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in names])
data=dict(source=source,target=original['target'],clips={'RevolverCrouchAimReloadInit':dict(asset=clip.get_path_name(),duration=clip.get_play_length())})
(OUT/'source-crouch-init-bind.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
runpy.run_path(str(OUT/'retarget_source.py'),init_globals={'RETARGET_INPUT':'source-crouch-init-bind.json','RETARGET_VARIANT':'CrouchInitBind_'})
