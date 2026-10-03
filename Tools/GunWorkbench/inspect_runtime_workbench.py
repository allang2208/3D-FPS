"""Read the actual nearby workbench instances in the user's running scene."""
import json,datetime
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/GunWorkbenchVisibleFix20260928')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if not world:raise RuntimeError('No running game world; keep the reported scene running for this read')
def path(obj):return obj.get_path_name() if obj else None
def prop(obj,name):
    try:return obj.get_editor_property(name)
    except Exception as error:return 'unavailable: '+str(error)
def palette_info(palette):
    if not palette:return None
    return {'path':path(palette),'entries':[{'id':str(e.get_editor_property('id')),'mesh':path(e.get_editor_property('mesh')),
        'actor_class':str(e.get_editor_property('actor_class'))} for e in palette.get_editor_property('components') if 'workbench' in str(e.get_editor_property('id'))]}
pc=u.GameplayStatics.get_player_controller(world,0);pawn=u.GameplayStatics.get_player_pawn(world,0)
result={'world':path(world),'player':path(pawn),'palettes':[],'instances':[]}
for owner in u.GameplayStatics.get_all_actors_of_class(world,u.VoxelBuildWorld):
    result['palettes'].append({'owner':path(owner),'palette':str(prop(owner,'palette'))})
if pc:
    component=pc.get_component_by_class(u.VoxelBuildComponent)
    if component:result['controller_palette_asset']=palette_info(component.get_editor_property('palette_asset'))
for actor in u.GameplayStatics.get_all_actors_of_class(world,u.VoxelBuildPrefabActor):
    for component in actor.get_components_by_class(u.StaticMeshComponent):
        mesh=component.static_mesh
        if not mesh or not ('GunWorkbench' in path(mesh) or 'WBStandalone_Workbench' in path(mesh)):continue
        ns=mesh.get_editor_property('nanite_settings')
        result['instances'].append({'actor':path(actor),'component':path(component),'mesh':path(mesh),
            'distance_cm':actor.get_distance_to(pawn) if pawn else None,'owner':path(actor.get_owner()),
            'transform':str(component.get_world_transform()),
            'disallow_nanite':prop(component,'disallow_nanite'),'force_disable_nanite':prop(component,'force_disable_nanite'),
            'nanite':{name:prop(ns,name) for name in ['enabled','fallback_percent_triangles','fallback_relative_error','keep_percent_triangles']},
            'materials':[path(component.get_material(i)) for i in range(component.get_num_materials())]})
result['instances'].sort(key=lambda e:e['distance_cm'] if e['distance_cm'] is not None else 0)
result['nanite_cvar']=u.SystemLibrary.get_console_variable_int_value('r.Nanite')
filename='runtime-'+datetime.datetime.now().strftime('%H%M%S')+'.json'
(ROOT/filename).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('WORKBENCH_RUNTIME_STATE '+json.dumps({'file':filename,'world':result['world'],'palettes':result['palettes'],
    'nearest':[{k:e[k] for k in ['actor','mesh','distance_cm','disallow_nanite','force_disable_nanite','nanite']} for e in result['instances'][:5]],
    'nanite_cvar':result['nanite_cvar']},ensure_ascii=False))
