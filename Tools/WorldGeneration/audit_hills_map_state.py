"""Inspect saved and live hills component settings without opening or saving a map."""
import json
from pathlib import Path
import unreal as u

def fields(obj, names):
    result = {}
    for key in names:
        try:
            v = obj.get_editor_property(key)
            result[key] = v if isinstance(v,(str,bool,int,float)) or v is None else str(v)
        except Exception:
            pass
    return result

saved = u.load_asset('/Game/GameMaps/L_TemperateHills_Initial')
worlds = [saved] + list(u.EditorLevelLibrary.get_pie_worlds(False))
result = []
for world in worlds:
    if not world:
        continue
    row = {'world':world.get_path_name(), 'hills':[], 'pcg_world':[]}
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.TemperateHillsWorld):
        a = {'path':actor.get_path_name(), **fields(actor,['ready','surface_ready','seed','detail_radius_meters','view_radius_meters','assets'])}
        a['layers'] = []
        for c in actor.get_components_by_class(u.PCGComponent):
            info = {'path':c.get_path_name(), **fields(c,['activated','override_generation_radii',
                'generation_radii','is_component_partitioned','generation_trigger','override_scheduling_policy',
                'scheduling_policy','scheduling_policy_class','regenerate_in_editor'])}
            graph = c.get_graph()
            info['graph'] = graph.get_path_name() if graph else None
            try:
                p = c.get_editor_property('scheduling_policy')
                info['policy'] = fields(p,['use_frustum_culling','network_mode','direction_weight','use_distance','use_direction'])
            except Exception as e:
                info['policy_error'] = str(e)
            a['layers'].append(info)
        row['hills'].append(a)
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.PCGWorldActor):
        row['pcg_world'].append(fields(actor,['treat_player_controllers_as_generation_sources',
            'treat_editor_viewport_as_generation_source','enable_world_partition_generation_sources','use_2d_grid']))
    result.append(row)
Path('D:/FPS3D/FPSGAME/Saved/HillsDisappearanceAudit20261114/map-state.json').write_text(json.dumps(result,indent=2),encoding='utf8')
u.log('HILLS_MAP_STATE ' + json.dumps([{'world':r['world'],'hills':len(r['hills'])} for r in result]))
