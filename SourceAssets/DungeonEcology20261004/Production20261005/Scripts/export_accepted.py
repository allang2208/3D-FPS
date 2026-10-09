"""Serialize the accepted saved subject actors into runtime module descriptors.

Authoring conversion only: no generation, gameplay, rendering or map writes.
"""
from pathlib import Path
import copy,json,runpy,hashlib
import unreal as u
ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT.parent;PROJECT=SOURCE.parents[1]
rules=runpy.run_path(str(ROOT/'Scripts/extend_catalog.py'))
cfg=json.loads((SOURCE/'Config/room.json').read_text('utf8'))
draft=json.loads((SOURCE/'Config/modules-draft.json').read_text('utf8'))
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active PIE')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
previous=editor.get_editor_world() if editor else None
previous=previous.get_path_name().split('.')[0] if previous else None
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)

def vector(v):return [float(v.x),float(v.y),float(v.z)]
def asset(obj):return obj.get_path_name() if obj else ''
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
def transform(t,off):
    p=vector(t.translation);r=t.rotation.rotator()
    return dict(position=[p[i]-off[i] for i in range(3)],yaw=float(r.yaw),pitch=float(r.pitch),roll=float(r.roll),scale=vector(t.scale3d))
def materials(c):return [asset(c.get_material(i)) for i in range(c.get_num_materials())]
def part(c,t,off,tags,instanced=False):
    mesh=c.static_mesh
    if not mesh:return None
    p=dict(mesh=asset(mesh),**transform(t,off),materials=materials(c),
        collision=c.get_collision_enabled()!=u.CollisionEnabled.NO_COLLISION,fluid=False,
        cast_shadow=bool(c.get_editor_property('cast_shadow')),
        guardrail_drop='Traversal.GuardrailDrop' in tags,
        instanced=instanced or asset(mesh).startswith('/Game/PN_tropicalGroundPlants/'))
    p['affects_navigation']=p['collision']
    # Keep the accepted plant cluster's finite per-room draw range and stock LODs.
    distance=float(c.get_editor_property('ld_max_draw_distance'))
    if instanced:distance=max(distance,float(c.get_editor_property('instance_end_cull_distance')))
    if distance>0:p['max_draw_distance_cm']=distance
    if mesh.get_name().endswith('_Water'):p['fluid']=True;p['affects_navigation']=False
    return p

try:
    world=u.EditorLoadingAndSavingUtils.load_map(cfg['sample_map'])
    if not world:raise RuntimeError('Accepted ecology map unavailable')
    actors=AA.get_all_level_actors();modules=[];summary={}
    for original,room in zip(draft['modules'],cfg['rooms']):
        rid=room['id'];off=[room['offset'][0]*100,-room['offset'][1]*100,room['offset'][2]*100]
        m={k:copy.deepcopy(original[k]) for k in ('id','name','family_id','role','cells','ports','port_pairs')}
        # Occupancy ends at the real mating planes, as with the other core rooms.
        m['cells'][1]['min'][0]=m['ports'][0]['position'][0]
        m['cells'][2]['max'][0]=m['ports'][1]['position'][0]
        m['min']=[min(c['min'][i] for c in m['cells']) for i in range(3)]
        m['max']=[max(c['max'][i] for c in m['cells']) for i in range(3)]
        m.update(phase='production',random_pool_registered=True,revision=rules['REVISION'],
            selection=dict(chance_per_run=1,max_per_run=1,route='EcologyThemeOnly'),
            parts=[],runtime_actors=[],props=[],lights=[],anchors=[],side_sockets=[],scene_recipes=[],
            wall_finish='intact',scene_max_floor_props=0)
        interaction={s['id']:s for s in room.get('runtime_actors',[])}
        for a in actors:
            tags=[str(t) for t in a.tags]
            if rid not in tags or 'Ecology.Subject' not in tags:continue
            label=a.get_actor_label();at=transform(a.get_actor_transform(),off)
            if isinstance(a,u.ColdSteelSceneContainer):
                s=dict(type='scene_container',container_id=str(a.get_editor_property('container_id')).removeprefix('EcologySubject.'),
                    caption=str(a.get_editor_property('caption')),storage_pages=int(a.get_editor_property('storage_pages')),
                    body=asset(a.body.static_mesh),door=asset(a.door.static_mesh),
                    body_materials=materials(a.body),door_materials=materials(a.door),
                    hinge=vector(a.door_hinge.get_editor_property('relative_location')),
                    opened_yaw=float(a.get_editor_property('opened_yaw')),opened_roll=float(a.get_editor_property('opened_roll')),
                    initial_open_fraction=0.,drawer_travel=vector(a.get_editor_property('drawer_travel')),**at)
                motion=a.get_editor_property('opening_motion')
                s['opening_motion']='Drawer' if motion==u.ColdSteelContainerMotion.DRAWER else 'Lid' if motion==u.ColdSteelContainerMotion.LID else 'Swing'
                m['runtime_actors'].append(s);continue
            if isinstance(a,(u.WardGlassWindow,u.ColdSteelDoor)):
                spec=copy.deepcopy(interaction[label.removeprefix('EcoSubject_'+rid+'_')])
                for k in ('position_m','yaw_ue'):spec.pop(k,None)
                spec.update(at)
                if isinstance(a,u.WardGlassWindow):
                    pane=a.get_editor_property('glass_pane');spec['pane']=asset(pane.static_mesh)
                    for key,prop in [('fracture','fracture_mesh'),('fracture_material','fracture_material'),('impact_particles','impact_particles'),('sound','break_sound')]:spec[key]=asset(pane.get_editor_property(prop))
                    spec['dimensions_cm']=vector(pane.get_editor_property('pane_dimensions'))
                m['runtime_actors'].append(spec);continue
            if 'Ecology.UpperPlatformTreasure' in tags:
                spec=copy.deepcopy(next(p for p in room['props'] if p['identity']=='ecology_upper_platform'))
                spec.update(at);m['props'].append(spec);continue
            if isinstance(a,u.Light):
                c=a.get_component_by_class(u.LightComponent);color=c.get_light_color();rect=isinstance(a,u.RectLight)
                l=dict(type='rect' if rect else 'point',position=at['position'],pitch=at['pitch'],yaw=at['yaw'],roll=at['roll'],
                    intensity=float(c.get_editor_property('intensity')),radius=float(c.get_editor_property('attenuation_radius')),
                    color=[color.r,color.g,color.b],cast_shadows=bool(c.get_editor_property('cast_shadows')),
                    max_draw_distance_cm=float(c.get_editor_property('max_draw_distance')),
                    fade_range_cm=float(c.get_editor_property('max_distance_fade_range')),
                    indirect_lighting_intensity=float(c.get_editor_property('indirect_lighting_intensity')),
                    role=next((t.removeprefix('Dungeon.Light.') for t in tags if t.startswith('Dungeon.Light.')),'key'))
                l['optimized_radius_cm']=l['radius']
                if rect:
                    l['source_width_cm']=float(c.get_editor_property('source_width'));l['source_height_cm']=float(c.get_editor_property('source_height'))
                else:
                    l['source_radius']=float(c.get_editor_property('source_radius'));l['source_length']=float(c.get_editor_property('source_length'))
                m['lights'].append(l);continue
            if isinstance(a,u.AmbientSound):
                c=a.get_component_by_class(u.AudioComponent);attenuation=c.get_editor_property('attenuation_overrides')
                m['runtime_actors'].append(dict(type='ambient_sound',sound=asset(c.get_editor_property('sound')),
                    volume=float(c.get_editor_property('volume_multiplier')),
                    inner_radius_cm=attenuation.get_editor_property('attenuation_shape_extents').x,
                    falloff_cm=float(attenuation.get_editor_property('falloff_distance')),**at));continue
            components=a.get_components_by_class(u.StaticMeshComponent)
            for c in components:
                ct=tags+[str(t) for t in c.component_tags]
                if isinstance(c,u.InstancedStaticMeshComponent):
                    for i in range(c.get_instance_count()):
                        p=part(c,c.get_instance_transform(i,world_space=True),off,ct,True)
                        if p:m['parts'].append(p)
                else:
                    p=part(c,c.get_world_transform(),off,ct)
                    if p:m['parts'].append(p)
            if not components:raise RuntimeError('Unconverted ecology actor '+label)
        anchors=room['encounter_anchors_m']
        if rid=='EcoBiosphere':anchors=[[-17,0,0],[-12,-2.5,0],[-5,-3.4,0],[5,-3.4,0],[12,-1.8,0],[17,0,0],[0,8.4,0],[-5,14,3]]
        m['anchors']=[dict(role='encounter',position=[p[0]*100,-p[1]*100,p[2]*100]) for p in anchors]
        m['walk_polyline']=[p['position'] for p in m['ports']]
        if rid=='EcoBiosphere':m['walk_polyline']=[[p[0]*100,-p[1]*100,0] for p in [[-26,0],[-17,0],[-12,-2.5],[-5,-3.4],[5,-3.4],[12,-1.8],[17,0],[26,0]]]
        # Author paths reserve the corridor for dressing; no random floor clutter.
        m['walk_mask']=[dict(min=[m['min'][0],-150,-5],max=[m['max'][0],150,280])]
        pp=cfg['postprocess'];main=m['cells'][0]
        m['runtime_actors'].append(dict(type='post_process',position=[(main['min'][i]+main['max'][i])/2 for i in range(3)],
            extent=[(main['max'][i]-main['min'][i])/2 for i in range(3)],yaw=0,priority=2,blend_radius=120,
            exposure_ev=pp['exposure_ev'],exposure_bias=pp['exposure_bias'],bloom=pp['bloom'],vignette=pp['vignette'],
            indirect_intensity=1.,saturation=1.,contrast=1.))
        modules.append(m)
        summary[rid]=dict(parts=len(m['parts']),instanced_plants=sum(bool(p.get('instanced')) for p in m['parts']),
            containers=sum(s['type']=='scene_container' for s in m['runtime_actors']),lights=len(m['lights']),chests=len(m['props']))
    # Read the live saved catalog for established encounters, never replace it
    # with an older author mirror.
    production=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_Dungeon_Randomized')
    generators=u.GameplayStatics.get_all_actors_of_class(production,u.AuthoredDungeonGenerator)
    if len(generators)!=1:raise RuntimeError('Production generator unavailable')
    catalog=json.loads(generators[0].get_editor_property('module_catalog_json'))
    sources={m['id']:m for m in catalog['modules']}
    for m,source in zip(modules,('Distribution','Drainage','AbandonedFlueGasStation')):
        m['spawn']=copy.deepcopy(sources[source]['spawn'])
        m['spawn'].update(source='DungeonEcology20261004',theme='ecology',anchor_roles=['encounter'],sealed_encounter=True)
        m['runtime_assets']=sorted(set(rules['asset_paths'](m['runtime_actors']))|set(rules['asset_paths'](m['spawn'])))
    write(ROOT/'Config/modules.json',dict(revision=rules['REVISION'],sequence=rules['SEQUENCE'],modules=modules))
    disk=PROJECT/'Content/GameMaps/Design/L_Ecology_Theme_Subject.umap'
    write(ROOT/'Receipts/export.json',dict(stage='modules_exported',revision=rules['REVISION'],source_map=cfg['sample_map'],
        source_sha256=hashlib.sha256(disk.read_bytes()).hexdigest(),rooms=summary,tests_run=False,generated=False,rendered=False))
    print('ECOLOGY_ACCEPTED_MODULES_EXPORTED '+json.dumps(summary))
finally:
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower() and previous:
        u.EditorLoadingAndSavingUtils.load_map(previous)
