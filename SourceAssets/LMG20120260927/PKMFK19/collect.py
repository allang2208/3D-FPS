"""Read actual installed donor, target and reference bones for FK authoring."""
import json, hashlib
from pathlib import Path
import unreal as u

O = Path(__file__).resolve().parent
P = O.parents[2]
def tr(t):
    return {'p': list(t.translation.to_tuple()), 'q': [t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w], 's': list(t.scale3d.to_tuple())}
def sha(path):
    return hashlib.sha256((P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
out = {'meshes': {}, 'clips': {}}
for family, path in {
    'pkm': '/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular',
    '201': '/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10',
}.items():
    mesh = u.load_asset(path)
    dm, status = u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    _, rows = u.GeometryScript_BoneWeights.get_all_bones_info(dm)
    names = {b.index: str(b.name) for b in rows}
    bones = {str(b.name):dict(tr(b.world_transform),parent=names.get(b.parent_index)) for b in rows}
    out['meshes'][family] = {'asset':path,'sha256':sha(path),'skeleton':mesh.skeleton.get_path_name(),'bones':bones}
    for suffix in ('idle','reload','reload_empty'):
        asset = '/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_'+suffix if family=='pkm' else (
            '/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_idle' if suffix=='idle' else
            '/Game/Weapons/LMG201/Reload11/A_LMG201_'+suffix.replace('reload','reload_belt'))
        clip = u.load_asset(asset)
        model = clip.get_editor_property('data_model_interface')
        count = model.get_number_of_keys() if suffix!='idle' else 1
        opts = u.AnimPoseEvaluationOptions()
        opts.optional_skeletal_mesh = mesh
        opts.evaluation_type = u.AnimDataEvalType.SOURCE
        poses = []
        for i in range(count):
            pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip,clip.get_play_length()*i/max(1,count-1),opts)
            poses.append({n:{'local':tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)),
                             'world':tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD))} for n in bones})
        out['clips'][family+'_'+suffix] = {'asset':asset,'sha256':sha(asset),'seconds':clip.get_play_length(),
            'frames':count,'fps':[model.get_frame_rate().numerator,model.get_frame_rate().denominator],
            'poses':poses,'metadata':{str(k):str(v) for k,v in u.EditorAssetLibrary.get_metadata_tag_values(clip).items()}}
        print('PKMFK19_INPUT '+family+' '+suffix,flush=True)
(O/'input.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf8')
print('PKMFK19_INPUT_SAVED',flush=True)
