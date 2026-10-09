"""Read-only review of the accepted M-05 V04 assets; no actor spawn or save."""
import unreal as u
import json, math, bisect
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V04')
OUT=ROOT/'Review20261009';OUT.mkdir(exist_ok=True)
def path(o):return o.get_path_name() if o else None
def props(o,fields):
    result={}
    for f in fields:
        try:
            v=o.get_editor_property(f)
            result[f]=path(v) if isinstance(v,u.Object) else str(v) if not isinstance(v,(bool,int,float,str,list)) else v
        except Exception as e:result[f]={'unavailable':str(e)}
    return result
bp=u.load_asset('/Game/Monsters/FacelessResearcher/BP_FacelessResearcher');cdo=u.get_default_object(bp.generated_class())
mesh=cdo.get_editor_property('visual_mesh');skeleton=mesh.get_editor_property('skeleton')
combat=cdo.get_editor_property('combat');knock=cdo.get_editor_property('knockdown')
report={'blueprint':path(bp),'class':path(cdo.get_class()),'mesh':path(mesh),'skeleton':path(skeleton),
    'tags':[str(v) for v in cdo.get_editor_property('tags')],
    'character':props(cdo,['contact_time','contact_end','recovery_time','walk_speed','attack_range','max_health','attack_damage']),
    'component':props(cdo.get_editor_property('mesh'),['skeletal_mesh_asset','relative_location','relative_scale3d','animation_mode','anim_class']),
    'combat':props(combat,['hit_clip','dizzy_clip','dizzy_play_rate']),
    'knockdown':props(knock,['enabled','fall_clip','get_up_clip','prone_get_up_clip']),
    'meshes':{},'clips':{},'problems':[], 'runtime_executed':False,'assets_modified':False}
expected=json.loads((ROOT/'stable_curves.json').read_text(encoding='utf-8'))
source=json.loads((ROOT/'waist_source.json').read_text(encoding='utf-8'))
for candidate in [mesh,u.load_asset('/Game/Monsters/FacelessResearcher/SK_FacelessResearcher_Clothing_V04')]:
    report['meshes'][path(candidate)]={'skeleton':path(candidate.get_editor_property('skeleton')),
        'physics':path(candidate.get_editor_property('physics_asset')),
        'morph_names':[v.get_name() for v in candidate.get_editor_property('morph_targets')],
        'materials':[path(v.get_editor_property('material_interface')) for v in candidate.get_editor_property('materials')],
        'lods':u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(candidate)}

def sample(times,values,t):
    k=bisect.bisect_right(times,t)
    if k==0:return values[0]
    if k==len(times):return values[-1]
    alpha=(t-times[k-1])/max(1.e-9,times[k]-times[k-1])
    return values[k-1]*(1-alpha)+values[k]*alpha

for role in ['idle','walk','attack','hit','dizzy']:
    clip=(combat if role in ['hit','dizzy'] else cdo).get_editor_property(role+'_clip')
    if not clip:report['clips'][role]=None;continue
    curves=[str(n) for n in u.AnimationLibrary.get_animation_curve_names(clip,u.RawCurveTrackTypes.RCT_FLOAT)]
    record={'path':path(clip),'skeleton':path(clip.get_editor_property('skeleton')),'duration':clip.get_play_length(),
        'rate_scale':clip.get_editor_property('rate_scale'),'curve_names':curves}
    if role in expected:
        record['missing_curves']=sorted(set(expected[role])-set(curves))
        record['legacy_curves']=[n for n in curves if n.startswith(('FRS1_','FRS2_','FRS3_'))]
        tracks={n:u.AnimationLibrary.get_float_keys(clip,n) for n in expected[role] if n in curves}
        count=round(clip.get_play_length()*30)+1
        totals=[sum(sample(ts,vs,min(f/30.,clip.get_play_length())) for ts,vs in tracks.values()) for f in range(count)]
        record['curve_weight_sum_range']=[min(totals),max(totals)]
        record['maximum_saved_key_error']=max([max(abs(a-b) for a,b in zip(tracks[n][1],expected[role][n])) for n in tracks] or [0])
        record['source']=source['clips'][role]['source']
    report['clips'][role]=record

# Read the exact shared fallbacks selected for a Nurse-derived researcher.
for role,name in [('fall','Hit_Knockback'),('get_up','LayToIdle'),('prone_get_up','ProneToIdle')]:
    assigned=knock.get_editor_property(role+'_clip')
    fallback=u.load_asset('/Game/Monsters/HumanoidKnockdown/Nurse/A_Nurse_'+name)
    report['clips'][role]={'assigned':path(assigned),'fallback':path(fallback),
        'assigned_skeleton':path(assigned.get_editor_property('skeleton')) if assigned else None,
        'fallback_skeleton':path(fallback.get_editor_property('skeleton')) if fallback else None}
fallback=u.load_asset('/Game/Monsters/HumanoidStun/Nurse/A_Nurse_Dizzy')
report['dizzy_fallback']={'path':path(fallback),'skeleton':path(fallback.get_editor_property('skeleton')) if fallback else None}
report['physics']=props(mesh.get_editor_property('physics_asset'),['skeletal_body_setups','constraint_setup'])
# Objects inside array-valued properties are serialized as paths, not modified.
def default(v):return path(v) if isinstance(v,u.Object) else str(v)
(OUT/'assets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=default),encoding='utf-8')
print('M05_READ_ONLY_ASSET_REVIEW '+json.dumps({'mesh':path(mesh),'skeleton':path(skeleton),'output':str(OUT/'assets.json')},ensure_ascii=False))
