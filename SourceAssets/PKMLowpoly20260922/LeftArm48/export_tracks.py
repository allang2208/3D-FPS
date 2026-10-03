"""Export the installed PKM poses at native key times for an asset-only repair."""
import hashlib,json
from pathlib import Path
import unreal as u

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
OUT=HERE/'InputTracks'; OUT.mkdir(exist_ok=True)
snapshot=json.loads((HERE/'current_mesh.json').read_text())
mesh=u.load_asset(snapshot['source'])
names=['upperarm_l','upperarm_twist_02_l','lowerarm_l','lowerarm_twist_02_l','lowerarm_twist_01_l','hand_l']
def pack(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return {'p':[p.x,p.y,p.z],'q':[q.x,q.y,q.z,q.w],'s':[s.x,s.y,s.z]}
base='/Game/Weapons/PKMLowpoly20260922'
folders=[base+'/Animations']+[base+'/Accessories14/Animations/'+f for f in ['angled','canted','prism','vertical']]
manifest=[]
for folder in folders:
    for path in sorted(u.EditorAssetLibrary.list_assets(folder,False,False)):
        anim=u.load_asset(path)
        if not isinstance(anim,u.AnimSequence): continue
        model=anim.get_editor_property('data_model_interface')
        count=model.get_number_of_keys(); duration=anim.get_play_length()
        opt=u.AnimPoseEvaluationOptions(); opt.optional_skeletal_mesh=mesh; opt.evaluation_type=u.AnimDataEvalType.RAW
        rows=[]
        for i in range(count):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,duration*i/max(1,count-1),opt)
            rows.append({n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names})
        file=PROJECT/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
        row={'asset':anim.get_path_name(),'duration':duration,'keys':count,'source_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
             'import_source':anim.get_editor_property('asset_import_data').get_first_filename(),'frames':rows}
        dest=OUT/(anim.get_name()+'.json')
        dest.write_text(json.dumps(row,separators=(',',':')),encoding='utf-8')
        manifest.append({k:v for k,v in row.items() if k!='frames'})
        print('PKM_ARM_SOURCE',anim.get_name(),count,flush=True)
(HERE/'track_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('PKM_ARM_SOURCES_COMPLETE',len(manifest))
