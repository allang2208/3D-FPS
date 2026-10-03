"""Recover the four actual Contact15 idle actions discarded by Elbow39's source-name error."""
import json
from pathlib import Path
import unreal as u

HERE=Path(__file__).resolve().parent
OUT=HERE/'RestoredContacts';OUT.mkdir(exist_ok=True)
d=json.loads((HERE/'current_mesh.json').read_text())
mesh=u.load_asset(d['source']); E=u.EditorAssetLibrary
indices={b['index']:n for n,b in d['bones'].items()}
def in_left_arm(n):
    while n:
        if n=='clavicle_l':return True
        n=indices.get(d['bones'][n]['parent'])
    return False
left=[n for n in d['bones'] if in_left_arm(n)]
names=['upperarm_l','upperarm_twist_02_l','lowerarm_l','lowerarm_twist_02_l','lowerarm_twist_01_l','hand_l']
def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return {'p':[p.x,p.y,p.z],'q':[q.x,q.y,q.z,q.w],'s':[s.x,s.y,s.z]}
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
try:
    u.SystemLibrary.execute_console_command(None,flag+' 0')
    for family in ['angled','canted','prism','vertical']:
        name='A_PKM_'+family+'_idle'
        src=json.loads((HERE/'InputTracks'/(name+'.json')).read_text())
        source=HERE.parent/'GripContact15/Animations'/family/(name+'.fbx')
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.import_mesh=False;opt.import_animations=True
        opt.import_materials=False;opt.import_textures=False;opt.skeleton=mesh.skeleton
        opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
        task=u.AssetImportTask();task.filename=str(source)
        task.destination_path='/Game/Weapons/PKMLowpoly20260922/LeftArm48/ContactSources'
        task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=True
        task.options=opt;task.factory=u.FbxFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        anim=u.load_asset(task.destination_path+'/'+name)
        if not anim:raise RuntimeError('Contact source import failed '+name)
        count=anim.get_editor_property('data_model_interface').get_number_of_keys()
        if count!=src['keys']:raise RuntimeError('Contact idle key count changed')
        options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh;options.evaluation_type=u.AnimDataEvalType.RAW
        frames=[];local={n:[] for n in left}
        for i in range(count):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,src['duration']*i/(count-1),options)
            frames.append({n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names})
            for n in left:local[n].append(pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)))
        src['frames']=frames;src['restored_contact_tracks']=local
        src['contact_source']=str(source);src['contact_action']='A_PKM_'+family+'_idle_Contact15'
        (OUT/(name+'.json')).write_text(json.dumps(src,separators=(',',':')),encoding='utf-8')
        print('CONTACT_SOURCE_RECOVERED',family,count)
finally:
    u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
