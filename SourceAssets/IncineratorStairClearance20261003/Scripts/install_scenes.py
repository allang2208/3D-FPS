"""Clear the observation stair intrusion by separating the existing subject rooms."""
import hashlib
import json
import math
import runpy
import shutil
import traceback
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
LINE=ROOT.parent/'DungeonIncineratorLine20261003'
TARGET='/Game/GameMaps/Design/L_Incinerator_Theme_Subject'
PRODUCTION='/Game/GameMaps/L_Dungeon_Randomized'
read=lambda p:json.loads(p.read_text('utf-8-sig'))
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
def backup(path):
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    dest=ROOT/'Backup'/(path.stem+'-'+sha[:12]+path.suffix)
    dest.parent.mkdir(exist_ok=True)
    if not dest.exists():shutil.copy2(path,dest)
    return sha

existing=globals().get('STAIR_CLEARANCE_EXISTING_EDITOR',False)
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and not existing:
    raise RuntimeError('Commandlet or existing editor bridge required')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():raise RuntimeError('Preserve active play session')
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
if dirty:raise RuntimeError('Preserve unsaved maps: '+str(dirty))
original=editor.get_editor_world()
original=original.get_path_name().split('.')[0] if original else ''
rules=runpy.run_path(str(LINE/'Scripts/subject_layout.py'))
line=read(LINE/'Config/line.json')
if line.get('layout_revision')==rules['REVISION']:
    print('STAIR_INTRUSION_ALREADY_REMOVED',TARGET)
else:
    report=dict(stage='saving',map=TARGET,tests_run=False,game_run=False,rendered=False,editor_opened=False,
        cause='First room discovery wing overlapped second room observation stairs in the fixed subject layout',
        production_changed=False,production_rule='AuthoredDungeonGenerator FPlan::Place rejects overlapping occupied cells')
    receipt=ROOT/'Receipts/install.json'
    try:
        write(receipt,report)
        source=read(LINE/'Config/source-modules.json')
        modules={m['id']:m for m in source['modules']}
        world=u.EditorLoadingAndSavingUtils.load_map(PRODUCTION)
        generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
        if len(generators)!=1:raise RuntimeError('Production connector source unavailable')
        live=json.loads(generators[0].get_editor_property('module_catalog_json'))
        modules['Threshold']=next(m for m in live['modules'] if m['id']=='Threshold')
        placements=rules['placements'](modules,line['sequence'])
        key=lambda p:p.get('name',p['id'])
        old={key(p):p for p in line['placements']}
        new={key(p):p for p in placements}
        if not old.keys()<=new.keys():raise RuntimeError('Preserve existing subject rooms')
        deltas={k:[new[k]['position'][i]-p['position'][i] for i in range(3)] for k,p in old.items()}
        report.update(previous_map_sha256=backup(PROJECT/'Content/GameMaps/Design/L_Incinerator_Theme_Subject.umap'),
                      room_offsets=deltas,previous_placements=line['placements'],placements=placements)
        world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
        if not world:raise RuntimeError('Retained subject map unavailable')
        actors=u.get_editor_subsystem(u.EditorActorSubsystem)
        current=list(actors.get_all_level_actors())
        template=[a for a in current if 'SupportHallLink' in [str(t) for t in a.tags]]
        if not template:raise RuntimeError('Original fixed connector unavailable')
        moved=[]
        for actor in current:
            tags=[str(t) for t in actor.tags]
            if 'IncineratorLine.Subject' not in tags:continue
            identity=next((k for k in old if k in tags),None)
            delta=deltas.get(identity,[0,0,0])
            if actor.get_actor_label()=='IncineratorLine_EndCap':delta=deltas[line['sequence'][-1]]
            if not any(abs(v)>.001 for v in delta):continue
            actor.modify()
            actor.set_actor_location(actor.get_actor_location()+u.Vector(*delta),False,False)
            moved.append(actor.get_actor_label())
        cache={}
        def asset(path):
            if path not in cache:
                cache[path]=u.load_asset(path)
                if not cache[path]:raise RuntimeError('Missing connector asset '+path)
            return cache[path]
        added=[]
        for pose in placements:
            name=key(pose)
            if name in old:continue
            if pose['id']=='Transit':
                delta=[pose['position'][i]-old['SupportHallLink']['position'][i] for i in range(3)]
                for actor in template:
                    # Actor duplication uses editor transaction/UI state that is
                    # unavailable in a commandlet. Author the same components directly.
                    clone=actors.spawn_actor_from_class(actor.get_class(),actor.get_actor_location()+u.Vector(*delta),actor.get_actor_rotation())
                    if not clone:raise RuntimeError('Connector authoring failed')
                    clone.set_actor_scale3d(actor.get_actor_scale3d())
                    if isinstance(actor,u.StaticMeshActor):
                        source_component=actor.static_mesh_component
                        c=clone.static_mesh_component
                        c.set_mobility(u.ComponentMobility.STATIC)
                        c.set_static_mesh(source_component.static_mesh)
                        c.set_collision_profile_name(source_component.get_collision_profile_name())
                        c.set_cast_shadow(source_component.get_editor_property('cast_shadow'))
                        for slot in range(source_component.get_num_materials()):
                            c.set_material(slot,source_component.get_material(slot))
                    elif isinstance(actor,(u.SpotLight,u.PointLight)):
                        source_component=actor.get_component_by_class(u.PointLightComponent)
                        c=clone.get_component_by_class(u.PointLightComponent)
                        c.set_mobility(u.ComponentMobility.MOVABLE)
                        for prop in ('intensity_units','intensity','attenuation_radius','cast_shadows',
                                     'source_radius','source_length','indirect_lighting_intensity',
                                     'volumetric_scattering_intensity','max_draw_distance','max_distance_fade_range'):
                            c.set_editor_property(prop,source_component.get_editor_property(prop))
                        c.set_light_color(source_component.get_light_color())
                        if isinstance(actor,u.SpotLight):
                            for prop in ('outer_cone_angle','inner_cone_angle'):
                                c.set_editor_property(prop,source_component.get_editor_property(prop))
                    else:raise RuntimeError('Unexpected connector actor '+actor.get_class().get_name())
                    label=actor.get_actor_label().replace('SupportHallLink',name,1)
                    clone.set_actor_label(label)
                    clone.set_folder_path('IncineratorLine/'+name)
                    clone.set_editor_property('tags',[u.Name(name if str(t)=='SupportHallLink' else str(t)) for t in actor.tags])
                    added.append(label)
            elif pose['id']=='Threshold':
                for index,spec in enumerate(modules['Threshold']['parts']):
                    pos=rules['transform'](spec.get('position',[0,0,0]),pose)
                    actor=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*pos),
                        u.Rotator(pitch=spec.get('pitch',0),yaw=pose['yaw']+spec.get('yaw',0),roll=spec.get('roll',0)))
                    if not actor:raise RuntimeError('Threshold authoring failed')
                    label='IncineratorLine_'+name+'_'+str(index)
                    actor.set_actor_label(label);actor.set_folder_path('IncineratorLine/'+name)
                    actor.set_editor_property('tags',[u.Name('IncineratorLine.Subject'),u.Name(name)])
                    c=actor.static_mesh_component;c.set_mobility(u.ComponentMobility.STATIC)
                    c.set_static_mesh(asset(spec['mesh']))
                    c.set_collision_profile_name('BlockAll' if spec.get('collision',True) else 'NoCollision')
                    c.set_cast_shadow(spec.get('cast_shadow',True))
                    for index,path in enumerate(spec.get('materials',[])):
                        if path:c.set_material(index,asset(path))
                    actor.set_actor_scale3d(u.Vector(*spec.get('scale',[1,1,1])))
                    added.append(label)
            else:raise RuntimeError('Unexpected connector '+pose['id'])
        if not u.EditorLoadingAndSavingUtils.save_map(world,TARGET):raise RuntimeError('Subject map save failed')
        backup(LINE/'Config/line.json')
        line.update(placements=placements,layout_revision=rules['REVISION'],
            stair_intrusion_removed=True,layout_reason=report['cause'])
        write(LINE/'Config/line.json',line)
        backup(LINE/'Config/source-modules.json')
        source['modules']=[*source['modules'],modules['Threshold']] if not any(m['id']=='Threshold' for m in source['modules']) else source['modules']
        write(LINE/'Config/source-modules.json',source)
        report.update(stage='map_saved',moved_actor_count=len(moved),added_actor_count=len(added),
            moved_actors=moved,added_actors=added,layout_revision=rules['REVISION'])
        write(receipt,report)
        print('STAIR_INTRUSION_REMOVED_MAP_SAVED',TARGET,'moved',len(moved),'connector parts',len(added))
    except Exception:
        report.update(stage='save_failed',error=traceback.format_exc());write(receipt,report);raise
    finally:
        if existing and original and u.EditorAssetLibrary.does_asset_exist(original):
            u.EditorLoadingAndSavingUtils.load_map(original)
