"""Read-only diagnosis of the currently installed ordinary hammer animation."""
import json
from pathlib import Path
import unreal as u

P=Path(__file__).resolve().parent
R=P.parents[2]
if Path(u.Paths.project_dir()).resolve()!=R:
    raise RuntimeError('Wrong project')
mesh=u.load_asset('/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1')
options=u.AnimPoseEvaluationOptions()
options.evaluation_type=u.AnimDataEvalType.SOURCE
options.optional_skeletal_mesh=mesh
def vec(v):return [v.x,v.y,v.z]
def transform(t):return {'p':vec(t.translation),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':vec(t.scale3d)}
report={'mesh':mesh.get_path_name(),'clips':{},'profiles':{},'models':{},'evaluation_types':str(list(u.AnimDataEvalType))}
folder='/Game/Weapons/SteelWarhammer20261014/NormalComboV4/'
for stage in range(1,4):
    for suffix in ('','Recover'):
        name=f'A_Warhammer_Slash{stage}{suffix}'
        anim=u.load_asset(folder+name)
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,0.,options)
        bones=list(u.AnimPoseExtensions.get_bone_names(pose))
        rows=[]
        for i in range(121):
            t=anim.get_play_length()*i/120
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,t,options)
            all_pose={str(n):transform(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in bones}
            rows.append({'t':t,'pose':all_pose})
        report['clips'][name]={'duration':anim.get_play_length(),'metadata':{str(k):str(v) for k,v in u.EditorAssetLibrary.get_metadata_tag_values(anim).items()},'samples':rows}
profile=u.load_asset('/Game/Weapons/SteelWarhammer20261014/RhythmClearanceV2/DA_Warhammer_Clearance')
for clip in profile.get_editor_property('clips'):
    base=clip.get_editor_property('base')
    report['profiles'][base.get_path_name()]=[str(t.get_editor_property('bone')) for t in clip.get_editor_property('tracks')]
cat=json.loads((R/'Content/ColdSteelData/thunder-god-hammer-modules.json').read_text(encoding='utf-8'))
for name in ('factory','static_field_grip','coil_grip'):
    spec=cat['slots']['grip'][name]
    asset=u.load_asset(spec['mesh'])
    bounds=asset.get_bounds()
    report['models'][name]={'spec':spec,'origin':vec(bounds.origin),'extent':vec(bounds.box_extent)}
(P/'native_before.json').write_text(json.dumps(report,ensure_ascii=False),encoding='utf-8')
print('HAMMER_GRIP_NATIVE_READ '+json.dumps({'clips':{n:{k:v for k,v in row.items() if k!='samples'} for n,row in report['clips'].items()},'profiles':report['profiles'],'models':report['models'],'evaluation_types':report['evaluation_types']},ensure_ascii=False))
