"""Requested asset/configuration audit in a fresh commandlet. No physics or PIE."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from playable_config import ROOT, MAP, SCALE
import unreal as u

E=u.EditorAssetLibrary
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
saved=json.loads((ROOT/'import_saved.json').read_text())
expected=json.loads((ROOT/'level_saved.json').read_text())
report={'map':MAP,'errors':[],'meshes':{},'doors':[],'lights':[],'runtime_tested':False}
def check(ok,msg):
    if not ok:report['errors'].append(msg)
def vec(v):return [v.x,v.y,v.z]
world=u.EditorLoadingAndSavingUtils.load_map(MAP)
if not world:raise RuntimeError('Cannot reopen saved map')
actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
check(world.get_world_settings().get_editor_property('default_game_mode').get_path_name()==expected['game_mode'],'GameMode')
for name,row in saved['meshes'].items():
    m=E.load_asset(row['path'])
    body=m.get_editor_property('body_setup')
    agg=body.get_editor_property('agg_geom')
    slots=m.get_editor_property('static_materials')
    check(all(s.material_interface for s in slots),'Material slots '+name)
    props={'collision_flag':str(body.get_editor_property('collision_trace_flag')),
           'convex':len(agg.get_editor_property('convex_elems')),
           'boxes':len(agg.get_editor_property('box_elems')),
           'nanite':bool(m.get_editor_property('nanite_settings').enabled),
           'lods':SM.get_lod_count(m),'materials':[s.material_interface.get_path_name() for s in slots]}
    check(props['nanite']==row['nanite'],'Nanite '+name)
    check(props['lods']==row['lods'],'LODs '+name)
    check(props['convex']==0,'Room-enclosing convex '+name)
    if name.startswith('DoorAsset_') and name.endswith('_Leaf'):
        check(props['boxes']==1,'Door leaf collision '+name)
    report['meshes'][name]=props
for row in expected['actors']:
    a=actors.get(row['label'])
    check(a is not None,'Missing actor '+row['label'])
    if not a:continue
    check(a.static_mesh_component.get_editor_property('static_mesh').get_path_name()==row['mesh'],'Mesh reference '+row['label'])
    check(all(abs(x-SCALE)<1e-5 for x in vec(a.get_actor_scale3d())),'Scene scale '+row['label'])
    coll=a.static_mesh_component.get_collision_enabled()!=u.CollisionEnabled.NO_COLLISION
    check(coll==row['collision'],'Collision enabled '+row['label'])
for row in expected['doors']:
    a=actors[row['label']]
    parts={c.get_name():c for c in a.get_components_by_class(u.StaticMeshComponent)}
    check(all(abs(x-1)<1e-5 for x in vec(a.get_actor_scale3d())),'Native door scale '+row['label'])
    check(abs(a.get_actor_rotation().yaw-row['yaw'])<1e-4,'Door axis '+row['label'])
    p={n:{'mesh':c.get_editor_property('static_mesh').get_path_name(),
          'relative_location':vec(c.get_editor_property('relative_location')),
          'relative_scale':vec(c.get_editor_property('relative_scale3d'))} for n,c in parts.items()}
    for n in ('LeafLeft','LeafRight'):
        check('/CyberpunkApartmentPlayable20261021/' in p[n]['mesh'],'Default leaf left in '+row['label'])
    report['doors'].append(dict(label=row['label'],parts=p,
        slide_cm=a.get_editor_property('slide_distance_cm'),autoclose=a.get_editor_property('auto_close_seconds')))
for row in expected['lights']:
    a=actors[row['label']]
    f=a.get_actor_forward_vector()
    c=a.get_component_by_class(u.RectLightComponent)
    check(f.z<-.999,'Ceiling light points upwards: '+row['label'])
    report['lights'].append(dict(label=row['label'],world_forward=vec(f),
         max_draw_distance=c.get_editor_property('max_draw_distance'),radius=c.get_editor_property('attenuation_radius')))
rail=actors['CP_Guardrail_Balcony']
check('Traversal.GuardrailDrop' in [str(t) for t in rail.tags],'Rail traversal tag')
check(rail.static_mesh_component.get_collision_enabled()==u.CollisionEnabled.QUERY_AND_PHYSICS,'Rail query collision')
check('Traversal.GuardrailDrop' not in [str(t) for t in actors['S_balcony'].tags],'Privacy walls incorrectly tagged')
ps=actors['PlayerStart_Apartment']
report['spawn']=vec(ps.get_actor_location())
check(abs(report['spawn'][2]-100.25)<.01,'Spawn capsule centre')
check(len(u.GameplayStatics.get_all_actors_of_class(world,u.PlayerStart))==1,'Unexpected spawn count')
report['environment_actor_count']=len(expected['actors'])
report['proxy_count']=len(expected['collision_proxies'])
report['door_count']=len(expected['doors'])
report['stage']='saved_data_read_back' if not report['errors'] else 'issues_found'
(ROOT/'saved_readback.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if report['errors']:raise RuntimeError('; '.join(report['errors']))
u.log('CYBERPUNK_SAVED_DATA_READ_BACK')
