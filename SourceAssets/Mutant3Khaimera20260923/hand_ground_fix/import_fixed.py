"""Import the claw mesh and corrected motion as an isolated V2 asset family."""
import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).parent
DEST='/Game/Monsters/Mutant3Meshy/KhaimeraV2'
lib=u.EditorAssetLibrary
at=u.AssetToolsHelpers.get_asset_tools()
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
original=u.load_asset('/Game/Monsters/Mutant3Meshy/SK_Mutant3_Meshy')
skel_path=DEST+'/SK_Mutant3_Claw_Skeleton'
skeleton=u.load_asset(skel_path) or lib.duplicate_asset(original.skeleton.get_path_name(),skel_path)

def save(asset):
    if not lib.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())

def imp(file,name,path,options):
    task=u.AssetImportTask();task.filename=str(file);task.destination_name=name;task.destination_path=path
    task.options=options;task.automated=True;task.save=True;task.replace_existing=True
    at.import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('Import produced no asset: '+name)
    return u.load_asset(path+'/'+name)

o=u.FbxImportUI();o.automated_import_should_detect_type=False
o.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
o.import_as_skeletal=True;o.import_mesh=True;o.import_animations=False
o.import_materials=False;o.import_textures=False;o.create_physics_asset=False;o.skeleton=skeleton
o.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_COMPUTE_NORMALS
o.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
o.skeletal_mesh_import_data.set_editor_property('convert_scene_unit',True)
o.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
mesh=imp(ROOT/'SK_Mutant3_Claw.fbx','SK_Mutant3_Claw',DEST,o)
mesh.set_editor_property('materials',original.get_editor_property('materials'))
mesh.set_editor_property('physics_asset',original.get_editor_property('physics_asset'))
skeleton=mesh.skeleton
# The original body hierarchy and rest pose are preserved. Compatibility keeps
# the existing stagger/death clips usable, with the new fingers in neutral claw.
skeleton.set_editor_property('compatible_skeletons',[original.skeleton])
save(skeleton);save(mesh)
contract=json.loads((ROOT/'animation_contract.json').read_text())
delivery={'mesh':mesh.get_path_name(),'skeleton':skeleton.get_path_name(),
          'physics':mesh.get_editor_property('physics_asset').get_path_name(),'animations':{},'diagnosis':{}}
for role,info in contract['clips'].items():
    name='A_Mutant3_'+role
    o=u.FbxImportUI();o.automated_import_should_detect_type=False
    o.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;o.import_mesh=False;o.import_animations=True
    o.import_as_skeletal=True;o.import_materials=False;o.import_textures=False;o.skeleton=skeleton
    data=o.anim_sequence_import_data;data.set_editor_property('use_default_sample_rate',False)
    data.set_editor_property('custom_sample_rate',60);data.set_editor_property('convert_scene_unit',True)
    data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    clip=imp(ROOT/'final'/(name+'.fbx'),name,DEST+'/Animations',o)
    clip.set_preview_skeletal_mesh(mesh);clip.set_editor_property('loop',info['loop'])
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
    lib.set_metadata_tag(clip,'Revision','Khaimera V2: relaxed claw skin and foot-grounded pelvis 2026-09-23')
    lib.set_metadata_tag(clip,'SourceURL',contract['source_url']);save(clip)
    delivery['animations'][role]={'asset':clip.get_path_name(),'seconds':clip.get_play_length()}
    if role in ['FeralIdle','PounceWindup','PounceLand']:
        opts=u.AnimPoseEvaluationOptions();opts.set_editor_property('evaluation_type',u.AnimDataEvalType.RAW)
        opts.set_editor_property('optional_skeletal_mesh',mesh)
        samples=[]
        for i in range(round(clip.get_play_length()*60)+1):
            time=min(i/60,clip.get_play_length())
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,opts)
            samples.append({'time':time,'hips_z_cm':u.AnimPoseExtensions.get_bone_pose(pose,'Hips',u.AnimPoseSpaces.WORLD).translation.z})
        delivery['diagnosis'][role]=samples
save(skeleton)
contract['skeleton']=skeleton.get_path_name()
contract['state']='Claw mesh and nine corrected animations saved; targeted asset diagnosis performed; gameplay not tested'
(ROOT/'animation_contract.json').write_text(json.dumps(contract,indent=2),encoding='utf-8')
(ROOT/'import_delivery.json').write_text(json.dumps(delivery,indent=2),encoding='utf-8')
u.log('MUTANT3_CLAW_GROUND_IMPORTED '+str(len(delivery['animations'])))
