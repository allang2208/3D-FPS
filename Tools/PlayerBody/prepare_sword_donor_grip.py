"""Read the original UAL2 wrist/palm and elbow frames for rig fitting."""
import json
from pathlib import Path
import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/ThirdPersonSwordDonorRepair20261006')
source = json.loads((OUT/'imported-sources.json').read_text())
mesh = u.load_asset(source['mesh'])
if not mesh.skeleton:
    # Complete this task's initial legacy-FBX import, whose task.save omitted
    # the generated skeleton dependency. No existing production rig is edited.
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal = True
    options.import_mesh = True
    options.import_animations = False
    options.import_materials = False
    options.import_textures = False
    options.create_physics_asset = False
    task = u.AssetImportTask()
    task.filename = str(OUT/'Mannequin_F.fbx')
    task.destination_path = source['mesh'].rsplit('/',1)[0]
    task.destination_name = mesh.get_name()
    task.automated = True
    task.replace_existing = True
    task.save = True
    task.options = options
    task.factory = u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = u.load_asset(source['mesh'])
    if not mesh.skeleton:
        raise RuntimeError('Could not restore this task\'s donor skeleton')
    u.EditorAssetLibrary.save_loaded_asset(mesh.skeleton,False)
    u.EditorAssetLibrary.save_loaded_asset(mesh,False)
if not u.EditorAssetLibrary.does_asset_exist(next(p for n,p in source['clips'].items() if n.endswith('Sword_Heavy_Combo'))):
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_as_skeletal = False
    options.import_mesh = False
    options.import_animations = True
    options.skeleton = mesh.skeleton
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
    task = u.AssetImportTask()
    task.filename = str(OUT/'UAL2_Standard.fbx')
    task.destination_path = source['mesh'].rsplit('/',1)[0]
    task.destination_name = 'A_UAL2'
    task.automated = True
    task.replace_existing = False
    task.save = True
    task.options = options
    task.factory = u.FbxFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    for path in u.EditorAssetLibrary.list_assets(task.destination_path,True,False):
        if not u.EditorAssetLibrary.save_loaded_asset(u.load_asset(path),False):
            raise RuntimeError('Could not save donor dependency '+path)
names = source['bones']
component = u.new_object(u.SkeletalMeshComponent)
component.set_skeletal_mesh_asset(mesh)
parents = [names.index(str(component.get_parent_bone(n))) if str(component.get_parent_bone(n)) in names else -1 for n in names]
ref = mesh.skeleton.get_reference_pose()
options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = mesh
options.evaluation_type = u.AnimDataEvalType.SOURCE
def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
clips = {}
for name,path in source['clips'].items():
    if not name.endswith(('Sword_Heavy_Combo','Sword_Regular_Combo','Sword_Dash')):
        continue
    clip = u.load_asset(path)
    duration = clip.get_play_length()
    frames = []
    for i in range(round(duration*60)+1):
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip,min(i/60,duration),options)
        frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names])
    clips[name] = dict(asset=path,duration=duration,frames=frames)
result = dict(names=names,parents=parents,reference=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.WORLD)) for n in names],clips=clips)
(OUT/'original-poses.json').write_text(json.dumps(result,separators=(',',':')))
print('UAL2_ORIGINAL_GRIP_PREPARED')
