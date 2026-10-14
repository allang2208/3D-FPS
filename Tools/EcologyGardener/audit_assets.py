"""User-requested read-only ecology asset/default-object audit; no world mutation."""
import json,traceback
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/EcologyGardener20261014/Audit')
ROOT.mkdir(parents=True,exist_ok=True)
report={'checks':[],'defaults':{},'asset_mutations':False,'runtime_multiplayer_test':False}
def check(label,value,detail=None):
    report['checks'].append({'case':label,'pass':bool(value),'detail':detail})
def path(o):return o.get_path_name() if o else None
try:
    classes={
        'gardener':'/Game/Monsters/EcologyGardener/BP_EcologyGardener',
        'researcher':'/Game/Monsters/FacelessResearcher/BP_FacelessResearcher',
        'spiral':'/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14',
        'root_crown':'/Game/Monsters/RootCrown/BP_RootCrownRigPreview'}
    defaults={}
    for name,asset_path in classes.items():
        bp=u.load_asset(asset_path);check(name+'.blueprint_exists',bool(bp),asset_path)
        if not bp:continue
        cdo=u.get_default_object(bp.generated_class());defaults[name]=cdo
        info={'class':bp.generated_class().get_path_name(),'tags':[str(t) for t in cdo.get_editor_property('tags')]}
        for prop in ('replicates','replicate_movement','only_relevant_to_owner','max_health','walk_speed','rank'):
            try:info[prop]=str(cdo.get_editor_property(prop))
            except Exception:info[prop]='not_exposed'
        report['defaults'][name]=info
        check(name+'.replication_enabled',cdo.get_editor_property('replicates'))
        check(name+'.movement_replication',cdo.get_editor_property('replicate_movement'))
        check(name+'.visible_to_other_clients',not cdo.get_editor_property('only_relevant_to_owner'))
        check(name+'.AI_controller',bool(cdo.get_editor_property('ai_controller_class')))
    gardener=defaults['gardener'];researcher=defaults['researcher'];root=defaults['root_crown']
    mesh=gardener.get_editor_property('visual_mesh');original=researcher.get_editor_property('visual_mesh')
    check('gardener.current_V02_mesh',path(mesh)=='/Game/Monsters/EcologyGardener/V02/SK_EcologyGardener_V02.SK_EcologyGardener_V02',path(mesh))
    check('gardener.component_mesh_matches',gardener.get_editor_property('mesh').get_skeletal_mesh_asset()==mesh)
    check('gardener.shared_skeleton',mesh.get_editor_property('skeleton')==original.get_editor_property('skeleton'))
    check('gardener.shared_hit_physics',mesh.get_editor_property('physics_asset')==original.get_editor_property('physics_asset'))
    source_morphs={m.get_name() for m in original.get_editor_property('morph_targets')}
    morphs={m.get_name() for m in mesh.get_editor_property('morph_targets')}
    check('gardener.complete_FR_curves',source_morphs<=morphs,{'source':len(source_morphs),'gardener':len(morphs)})
    slots=[path(s.get_editor_property('material_interface')) for s in mesh.get_editor_property('materials')]
    check('gardener.seven_bound_materials',len(slots)==7 and all(slots),slots)
    check('gardener.no_global_material_override',len(gardener.get_editor_property('mesh').get_editor_property('override_materials'))==0)
    tags=report['defaults']['gardener']['tags']
    check('gardener.identity_and_animation_family','EcologyGardener' in tags and 'FacelessResearcher' in tags)
    components=[c.get_name() for c in gardener.get_components_by_class(u.ActorComponent)]
    check('gardener.status_replication_component','NetworkCombatStatus' in components,components)
    for prop in ('idle_clip','walk_clip','attack_clip'):
        clip=gardener.get_editor_property(prop)
        check('gardener.'+prop,bool(clip) and clip==researcher.get_editor_property(prop),path(clip))
    for group,props in [('combat',('hit_clip','dizzy_clip')),('knockdown',('fall_clip','get_up_clip','prone_get_up_clip'))]:
        a=gardener.get_editor_property(group);b=researcher.get_editor_property(group)
        for prop in props:
            clip=a.get_editor_property(prop);check('gardener.'+prop,bool(clip) and clip==b.get_editor_property(prop),path(clip))
    for prop in ('visual_mesh','hit_surface_physics','idle_clip','move_clip','turn_left_clip','turn_right_clip',
                 'slash_clip','slash_material','slash_arc_material','needle_clip','needle_mesh','needle_material',
                 'root_clip','root_knot_mesh','root_flesh_material','root_warning_material','mine_signal_material',
                 'stun_clip','air_clip','land_clip','get_up_clip','death_clip'):
        value=root.get_editor_property(prop);check('root_crown.'+prop,bool(value),path(value))
    hits=root.get_editor_property('hit_clips');check('root_crown.four_hit_directions',len(hits)==4 and all(hits))
    check('root_crown.slash_contact_frames',len(root.get_editor_property('slash_frames'))>2)
    report['failures']=sum(not item['pass'] for item in report['checks'])
    if report['failures']:raise RuntimeError('Ecology asset audit failed: %d checks'%report['failures'])
except Exception:
    report['error']=traceback.format_exc();raise
finally:
    (ROOT/'assets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('ECOLOGY_ASSET_AUDIT '+json.dumps({'checks':len(report['checks']),'failures':report.get('failures'),'error':report.get('error')}))
