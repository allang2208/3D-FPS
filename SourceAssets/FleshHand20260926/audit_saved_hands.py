"""User-requested read-only inspection of the saved giant/small hand assets.

Writes an audit report only; never compiles, modifies or saves UE packages,
spawns actors, opens a map, starts PIE, or renders a preview.
"""
from pathlib import Path
from datetime import datetime, timezone
import json
import math
import unreal as u

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
OUT=ROOT/'CompletionAudit20260927'
DEST='/Game/Monsters/FleshHand'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():
    raise RuntimeError('Wrong project')
OUT.mkdir(exist_ok=True)
report={'utc':datetime.now(timezone.utc).isoformat(),'mode':'read_only_saved_assets',
        'characters':{},'animations':{},'materials':{},'checks':[],
        'inspection_errors':[],'packages_saved':[],
        'runtime_tested':False,'visual_tested':False,'performance_tested':False}
def path(obj):return obj.get_path_name() if obj else None
def prop(obj,name):return obj.get_editor_property(name)
def check(name,result,detail=None):
    report['checks'].append({'name':name,'passed':bool(result),'detail':detail})
def optional(label,fn):
    try:return fn()
    except Exception as e:
        report['inspection_errors'].append({'item':label,'error':str(e)})
        return None
def vec(v):return [float(v.x),float(v.y),float(v.z)]
def clip_info(clip):
    return {'asset':path(clip),'seconds':float(clip.get_play_length()),
            'skeleton':path(prop(clip,'skeleton')),'rate_scale':float(prop(clip,'rate_scale')),
            'root_motion':bool(prop(clip,'enable_root_motion'))} if clip else None
def sample_animation(clip,mesh):
    options=u.AnimPoseEvaluationOptions()
    options.set_editor_property('optional_skeletal_mesh',mesh)
    samples=[]
    for fraction in (0.,.125,.25,.5,.75,1.):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,clip.get_play_length()*fraction,options)
        frame={}
        for bone in ('root','wrist','palm','index_02','middle_02','thumb_02'):
            t=u.AnimPoseExtensions.get_bone_pose(pose,bone,u.AnimPoseSpaces.LOCAL)
            frame[bone]=vec(t.translation)+[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w]+vec(t.scale3d)
        samples.append(frame)
    finite=all(math.isfinite(x) for s in samples for v in s.values() for x in v)
    changed=[bone for bone in samples[0] if any(max(abs(a-b) for a,b in zip(s[bone],samples[0][bone]))>1e-5 for s in samples[1:])]
    return {'sample_count':len(samples),'finite':finite,'moving_bones':changed,
            'root_translation_samples':[s['root'][:3] for s in samples],
            'root_scale_samples':[s['root'][7:] for s in samples]}

dirty_before={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
report['preexisting_dirty_hand_packages']=sorted(p for p in dirty_before if p.startswith(DEST+'/'))
mesh=u.load_asset(DEST+'/SK_FleshHand_Green')
if not mesh:raise RuntimeError('Missing hand mesh')
skeleton=prop(mesh,'skeleton')
mesh_editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
report['mesh']={'asset':path(mesh),'skeleton':path(skeleton),
                'lod_count':optional('mesh LOD count',lambda:mesh_editor.get_lod_count(mesh)),
                'physics_asset':path(prop(mesh,'physics_asset')),
                'materials':[path(prop(m,'material_interface')) for m in prop(mesh,'materials')]}
check('mesh has three LODs',report['mesh']['lod_count']==3,report['mesh']['lod_count'])
physics=prop(mesh,'physics_asset')
if physics:
    report['physics']=optional('query physics',lambda:{
        'bodies':len(prop(physics,'skeletal_body_setups')),
        'constraints':len(prop(physics,'constraint_setup'))})

kd_roles=('launch_palm','launch_back','air_palm','air_back','land_palm','land_back',
          'down_palm','down_back','get_up_palm','get_up_back')
for name,minion in (('BP_FleshHand',False),('BP_FleshHandMinion',True)):
    bp=u.load_asset(DEST+'/'+name)
    check(name+' exists',bp is not None)
    if not bp:continue
    cdo=u.get_default_object(bp.generated_class())
    skeletal=prop(cdo,'mesh');combat=prop(cdo,'combat');kd=prop(cdo,'knockdown')
    rotation=prop(skeletal,'relative_rotation');capsule=prop(cdo,'capsule_component')
    movement=prop(cdo,'character_movement')
    row={'class':path(bp.generated_class()),'mesh':path(prop(cdo,'visual_mesh')),
         'rotation':{'pitch':rotation.pitch,'yaw':rotation.yaw,'roll':rotation.roll},
         'scale':vec(prop(skeletal,'relative_scale3d')),
         'mesh_location':vec(prop(skeletal,'relative_location')),
         'materials':[path(m) for m in prop(skeletal,'override_materials')],
         'capsule':[prop(capsule,'capsule_radius'),prop(capsule,'capsule_half_height')],
         'tags':[str(t) for t in prop(cdo,'tags')],
         'ai_controller':path(prop(cdo,'ai_controller_class')),
         'stats':{key:prop(cdo,key) for key in ('minion','max_health','physical_attack','magic_defense','level','experience_reward','walk_speed','animation_walk_speed','corpse_seconds','slam_knockback_distance')},
         'clips':{},'retired':{key:path(prop(cdo,key)) for key in ('palm_fist_mesh','hammer_clip','minion_class')},
         'combat':{key:prop(combat,key) for key in ('toughness_threshold','toughness_break_seconds','stagger_duration','allow_subthreshold_stagger')},
         'knockdown_settings':{key:prop(kd,key) for key in ('enabled','launch_scale','ground_hold_seconds','fall_collision_radius')},
         'nav_agent':optional(name+' nav agent',lambda:str(prop(movement,'nav_agent_props')))}
    for key in ('idle_clip','move_clip','slam_clip','grand_slam_clip','death_clip','charge_windup_clip','charge_rush_clip','charge_recover_clip'):
        row['clips'][key]=clip_info(prop(cdo,key))
    row['clips']['hit_clip']=clip_info(prop(combat,'hit_clip'))
    row['clips']['dizzy_clip']=clip_info(prop(combat,'dizzy_clip'))
    for role in kd_roles:row['clips'][role+'_clip']=clip_info(prop(kd,role+'_clip'))
    required=['idle_clip','move_clip','death_clip','hit_clip','dizzy_clip']+[r+'_clip' for r in kd_roles]
    if not minion:required+=['slam_clip','grand_slam_clip','charge_windup_clip','charge_rush_clip','charge_recover_clip']
    for key in required:
        clip=row['clips'][key]
        check(name+' '+key,clip is not None and clip['seconds']>0 and clip['skeleton']==path(skeleton),clip)
    expected='A_FleshHand_WalkScurry' if minion else 'A_FleshHand_WalkWeighted'
    check(name+' latest locomotion',row['clips']['move_clip'] is not None and expected in row['clips']['move_clip']['asset'])
    check(name+' movement speed',abs(row['stats']['walk_speed']-(324 if minion else 259.2))<.001,row['stats']['walk_speed'])
    check(name+' palm forward upright',abs(rotation.pitch)<.01 and abs(rotation.roll)<.01 and abs(rotation.yaw-90)<.01,row['rotation'])
    check(name+' cancelled attacks unbound',all(v is None for v in row['retired'].values()),row['retired'])
    check(name+' knockdown enabled',row['knockdown_settings']['enabled'])
    if not minion:
        row['charge']={key:prop(cdo,key) for key in ('charge_min_range','charge_max_range','charge_windup_seconds','charge_cooldown','charge_speed','charge_distance','charge_damage_multiplier','charge_stun_seconds','charge_recover_seconds','charge_lead_strength','charge_max_lead_distance')}
        row['fx']={key:path(prop(cdo,key)) for key in ('impact_sound','warning_material','charge_dust_material','charge_air_material','charge_skin_material','charge_chip_material','charge_warning_material','charge_fx_plane','charge_fx_cube','charge_windup_sound','charge_rush_sound')}
        check(name+' FX references',all(row['fx'].values()),row['fx'])
    report['characters'][name]=row

ai=u.load_asset(DEST+'/BP_FleshHandAIController')
if ai:
    cdo=u.get_default_object(ai.generated_class())
    report['ai']={'behavior':path(prop(cdo,'behavior')),'memory_seconds':prop(cdo,'memory_seconds')}
check('shared behavior bound',bool(ai) and report['ai']['behavior']=='/Game/Monsters/AI/BT_Monster.BT_Monster')
# Inspect the actual saved packages even if the running editor's registry has
# not indexed this newly imported directory yet.
animation_paths={DEST+'/Animations/'+p.stem for p in (PROJECT/'Content/Monsters/FleshHand/Animations').glob('*.uasset')}
animation_paths.update(c['asset'].split('.')[0] for row in report['characters'].values() for c in row['clips'].values() if c)
for asset_path in sorted(animation_paths):
    clip=u.load_asset(asset_path)
    if not isinstance(clip,u.AnimSequence):continue
    data=clip_info(clip)
    data['sampled_pose']=optional(clip.get_name()+' pose',lambda:sample_animation(clip,mesh))
    report['animations'][clip.get_name()]=data
    check(clip.get_name()+' skeleton and length',data['seconds']>0 and data['skeleton']==path(skeleton))
    if data['sampled_pose']:
        check(clip.get_name()+' sampled animation',data['sampled_pose']['finite'] and bool(data['sampled_pose']['moving_bones']),data['sampled_pose']['moving_bones'])
for name in ('M_HandChargeAir','M_HandChargeDust','M_HandChargeTension','M_HandChargeChip','M_HandChargeWarning'):
    m=u.load_asset(DEST+'/ChargeVisual20260927/'+name)
    check(name+' exists',m is not None)
    if not m:continue
    code=[{'description':prop(n,'description'),'code':prop(n,'code')} for n in u.MaterialEditingLibrary.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)]
    report['materials'][name]={'asset':path(m),'blend_mode':str(prop(m,'blend_mode')),'custom_code':code}
    if name=='M_HandChargeAir':
        source=(ROOT/'ChargeAir.hlsl').read_text(encoding='utf-8')
        check('air material contains corrected source',any(n['code']==source for n in code))
dirty_after={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
report['new_dirty_hand_packages']=sorted(p for p in dirty_after-dirty_before if p.startswith(DEST+'/'))
report['summary']={'checks':len(report['checks']),'failed':[c for c in report['checks'] if not c['passed']],
                   'animation_count':len(report['animations']),'inspection_errors':len(report['inspection_errors'])}
(OUT/'saved_assets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('FLESHHAND_COMPLETION_AUDIT '+json.dumps(report['summary'],ensure_ascii=False))
