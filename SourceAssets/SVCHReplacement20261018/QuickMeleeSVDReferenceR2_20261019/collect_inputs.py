"""Read saved SVD and SVCH poses through the existing editor; no scene edits."""
from pathlib import Path
import unreal as u
import json, gzip, hashlib

O=Path(__file__).resolve().parent
I=O/'Inputs';I.mkdir(exist_ok=True)
P=Path(u.Paths.project_dir()).resolve()
manifest={}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def disk(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def digest(path):return hashlib.sha256(disk(path).read_bytes()).hexdigest()
def extract(asset):
    out={'family':str(asset.get_editor_property('family')),'clips':[]}
    for c in asset.get_editor_property('clips'):
        r=c.get_editor_property('retained')
        out['clips'].append({'base':c.get_editor_property('base').get_path_name().split('.')[0],
            'retained':r.get_path_name().split('.')[0] if r else None,'duration':c.get_editor_property('duration'),
            'tracks':[{'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),
                'values':list(t.get_editor_property('values'))} for t in c.get_editor_property('tracks')]})
    return out
paths={}
for f in ('base','angled','vertical','canted','prism'):
    paths['svd_'+f]='/Game/Weapons/SVDDragunov20260922/GripProfiles20261001/DA_SVD_Grip_'+f
    paths['svch_'+f]=('/Game/Weapons/SVCH/Replacement20261018/SightsR2/ElbowFit/DA_SVCH_ElbowFitGrip' if f=='base'
        else '/Game/Weapons/SVCH/Replacement20261018/ForegripFit20261019/DA_SVCH_Grip_'+f)
for key,path in paths.items():
    if not disk(path).exists():
        manifest[key]={'path':path,'exists':False};continue
    if path in dirty:raise RuntimeError('Unsaved source '+path)
    asset=u.load_asset(path)
    (I/(key+'.json')).write_text(json.dumps(extract(asset),separators=(',',':')))
    manifest[key]={'path':path,'sha256':digest(path)}
mesh=u.load_asset('/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock')
mod=u.SkeletonModifier();mod.set_skeletal_mesh(mesh);names=list(mod.get_all_bone_names());del mod
def xf(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
clips={}
for role in ('idle','quick_melee'):
    path='/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_'+role
    a=u.load_asset(path);duration=a.get_play_length();times=[min(n/120,duration) for n in range(round(duration*120)+1)]
    opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
    frames=[]
    for t in times:
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,opts)
        frames.append([xf(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
    clips[role]={'path':path,'sha256':digest(path),'duration':duration,'times':times,'frames':frames}
with gzip.open(I/'compressed.json.gz','wt') as f:json.dump({'names':[str(n) for n in names],'clips':clips},f,separators=(',',':'))
es=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=es.get_game_world() if es else None
manifest['editor']={'PIE':bool(world)}
if world:
    actors=u.GameplayStatics.get_all_actors_of_class(world,u.Character)
    state=[]
    for a in actors:
        if 'FPS' not in a.get_class().get_name():continue
        for c in a.get_components_by_class(u.SkeletalMeshComponent):
            m=c.get_skeletal_mesh_asset()
            if not m:continue
            state.append({'actor':a.get_name(),'component':c.get_name(),'mesh':m.get_path_name(),
                'visible':c.is_visible(),'relative':xf(c.get_relative_transform())})
    (I/'live-components.json').write_text(json.dumps(state,indent=2))
(I/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('SVCH_R2_INPUTS_SAVED',manifest['editor'],flush=True)
