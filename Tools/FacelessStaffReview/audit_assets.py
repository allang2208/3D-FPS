"""User-requested read-only M-03/M-04 motion audit; no actor spawn or asset save."""
import unreal as u
import json, math, bisect
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessStaffReview20261009')
OUT.mkdir(parents=True,exist_ok=True)
BONES=['head','pelvis','hand_l','hand_r','foot_l','foot_r','upperarm_l','upperarm_r']
def path(v):return v.get_path_name() if v else None
def value(v):
    if isinstance(v,u.Object):return path(v)
    if isinstance(v,(str,float,int,bool)) or v is None:return v
    return str(v)
def props(o,fields):
    return {f:value(o.get_editor_property(f)) for f in fields}
def sample(ts,vs,t):
    if not ts:return 0.
    k=bisect.bisect_right(ts,t)
    if k==0:return float(vs[0])
    if k==len(ts):return float(vs[-1])
    a=(t-ts[k-1])/max(1.e-9,ts[k]-ts[k-1]);return float(vs[k-1]*(1-a)+vs[k]*a)
def pose_at(clip,t,options):
    p=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options)
    result={}
    for b in BONES:
        tr=u.AnimPoseExtensions.get_bone_pose(p,b,u.AnimPoseSpaces.WORLD)
        result[b]={'p':[tr.translation.x,tr.translation.y,tr.translation.z],
            'q':[tr.rotation.x,tr.rotation.y,tr.rotation.z,tr.rotation.w]}
    return result
fallbacks={k:u.load_asset('/Game/Monsters/HumanoidKnockdown/Nurse/A_Nurse_'+v)
    for k,v in [('fall','Hit_Knockback'),('get_up','LayToIdle'),('prone_get_up','ProneToIdle')]}
fallbacks['dizzy']=u.load_asset('/Game/Monsters/HumanoidStun/Nurse/A_Nurse_Dizzy')
report={'assets_modified':False,'runtime_executed':False,'actors_spawned':False,'characters':{}}
report['editor_pie_already_running']=u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()
for identity,revision in [('Security','V11'),('Receptionist','V04')]:
    base='/Game/Monsters/Faceless'+identity
    bp=u.load_asset(base+'/BP_Faceless'+identity)
    cdo=u.get_default_object(bp.generated_class());mesh=cdo.get_editor_property('visual_mesh')
    skeleton=mesh.get_editor_property('skeleton');combat=cdo.get_editor_property('combat');knock=cdo.get_editor_property('knockdown')
    morphs={v.get_name() for v in mesh.get_editor_property('morph_targets')}
    cloth=u.load_asset(base+'/SK_Faceless'+identity+'_Clothing_'+revision)
    row={'blueprint':path(bp),'nurse_derived':isinstance(cdo,u.NurseZombie),
        'mesh':path(mesh),'skeleton':path(skeleton),'tags':[str(t) for t in cdo.get_editor_property('tags')],
        'character':props(cdo,['contact_time','contact_end','recovery_time','walk_speed','attack_range']),
        'component':props(cdo.get_editor_property('mesh'),['skeletal_mesh_asset','relative_location','relative_scale3d','animation_mode','anim_class']),
        'combat':props(combat,['hit_clip','dizzy_clip','dizzy_play_rate','stagger_duration']),
        'knockdown':props(knock,['enabled','fall_clip','get_up_clip','prone_get_up_clip']),
        'morph_names':sorted(morphs),'clothing':path(cloth),
        'clothing_morph_names':sorted(v.get_name() for v in cloth.get_editor_property('morph_targets')),
        'materials':[path(v.get_editor_property('material_interface')) for v in mesh.get_editor_property('materials')],
        'physics_asset':path(mesh.get_editor_property('physics_asset')),
        'lod_count':u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(mesh),'clips':{},'transitions':{}}
    options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.RAW;options.optional_skeletal_mesh=mesh
    poses={};curve_tracks={}
    for role in ['idle','walk','attack','hit','fall','get_up','prone_get_up','dizzy']:
        owner=knock if role in ['fall','get_up','prone_get_up'] else combat if role in ['hit','dizzy'] else cdo
        clip=owner.get_editor_property(role+'_clip');fallback=fallbacks.get(role)
        r={'assigned':path(clip),'fallback':path(fallback),'fallback_skeleton':path(fallback.get_editor_property('skeleton')) if fallback else None,
           'fallback_matches_mesh':fallback.get_editor_property('skeleton')==skeleton if fallback else None}
        if clip:
            length=clip.get_play_length();names=[str(n) for n in u.AnimationLibrary.get_animation_curve_names(clip,u.RawCurveTrackTypes.RCT_FLOAT)]
            tracks={n:u.AnimationLibrary.get_float_keys(clip,n) for n in names if n in morphs}
            curve_tracks[role]=tracks
            times=[min(i/30.,length) for i in range(math.ceil(length*30)+1)]
            sums=[sum(sample(ts,vs,t) for ts,vs in tracks.values()) for t in times]
            r.update({'duration':length,'rate_scale':clip.get_editor_property('rate_scale'),
                'skeleton':path(clip.get_editor_property('skeleton')),'skeleton_matches':clip.get_editor_property('skeleton')==skeleton,
                'curve_names':names,'matching_morph_curves':list(tracks),
                'unmatched_FR_curves':[n for n in names if n.startswith('FR') and n not in morphs],
                'morph_sum_range':[min(sums),max(sums)],
                'all_curve_values_finite':all(math.isfinite(float(v)) for ts,vs in tracks.values() for v in vs),
                'morph_metadata_missing':[n for n in tracks if not u.AnimationLibrary.get_curve_meta_data_morph_target(skeleton,n)]})
            poses[role]={'first':pose_at(clip,0.,options),'last':pose_at(clip,length,options)}
        row['clips'][role]=r
    for old,new in [('attack','idle'),('attack','walk'),('hit','idle'),('hit','walk'),('walk','walk'),('idle','idle')]:
        if old not in poses or new not in poses:continue
        metrics={}
        for bone in BONES:
            a=poses[old]['last'][bone];b=poses[new]['first'][bone]
            dot=min(1.,abs(sum(x*y for x,y in zip(a['q'],b['q']))))
            metrics[bone]={'distance_cm':math.dist(a['p'],b['p']),'rotation_degrees':math.degrees(2*math.acos(dot))}
        row['transitions'][old+'_to_'+new]=metrics
    # Raw keys retained so the author-data audit can use the exact saved curves.
    row['morph_curve_keys']={role:{n:[list(ts),list(vs)] for n,(ts,vs) in tracks.items()} for role,tracks in curve_tracks.items()}
    row['endpoint_poses_component_space_cm']=poses
    report['characters'][identity]=row
(OUT/'assets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M03_M04_READ_ONLY_REVIEW '+json.dumps({k:{'mesh':v['mesh'],'combat':v['combat'],'knockdown':v['knockdown']} for k,v in report['characters'].items()}))