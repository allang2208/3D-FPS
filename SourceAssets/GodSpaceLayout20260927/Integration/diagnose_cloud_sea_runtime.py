"""Read only the actual cloud/ocean bindings for the user's brown-plane report."""
import json
from pathlib import Path
import unreal as u
root=Path(__file__).parent
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if globals().get('LOAD_SAVED_HUB',False):
    u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/DayNight_Lighting')
def props(obj,names):
    result={}
    for name in names:
        try:result[name]=str(obj.get_editor_property(name))
        except Exception as e:result[name]='unavailable: '+str(e)
    return result
report={}
for title,world in [('editor',editor.get_editor_world()),('game',editor.get_game_world())]:
    if not world:continue
    rows=[]
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        atmosphere=a.get_components_by_class(u.SkyAtmosphereComponent)
        clouds=a.get_components_by_class(u.VolumetricCloudComponent)
        if atmosphere or clouds:
            row={'actor':a.get_path_name(),'tags':[str(t) for t in a.tags]}
            row['atmospheres']=[{'world_location':str(c.get_world_location()),**props(c,['transform_mode','absolute_location','absolute_rotation','bottom_radius','atmosphere_height','ground_albedo'])} for c in atmosphere]
            row['clouds']=[]
            for c in clouds:
                m=c.get_editor_property('material')
                row['clouds'].append({'material':m.get_path_name() if m else None,'parameters':props(m,['parent','scalar_parameter_values','vector_parameter_values','texture_parameter_values']) if m else {},**props(c,['visible','layer_bottom_altitude','layer_height','tracing_max_distance','tracing_start_max_distance','planet_radius','view_sample_count_scale'])})
            try:row['blueprint_settings']=json.loads(u.ToolsetLibrary.get_object_properties(a,['volumetric Cloud Settings']))
            except Exception:pass
            rows.append(row)
        if a.get_actor_label() in ['GodSpaceDistantOcean','GodSpaceDistantEarth']:
            c=a.get_component_by_class(u.StaticMeshComponent)
            rows.append({'ocean':a.get_path_name(),'location':str(a.get_actor_location()),'scale':str(a.get_actor_scale3d()),'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]})
    report[title]={'world':world.get_path_name(),'actors':rows}
for name in ['M_GodSpaceCloudSea','M_GodSpaceDistantOcean','M_GodSpaceOceanFar']:
    m=u.load_asset('/Game/Props/GodSpaceLayout20260927/Materials/'+name)
    report[name]=props(m,['material_domain','blend_mode','shading_model'])
for name in ['MI_GodSpaceDistantOcean','MI_GodSpaceOceanFar']:
    m=u.load_asset('/Game/Props/GodSpaceLayout20260927/Materials/'+name)
    report[name]=props(m,['parent','scalar_parameter_values','vector_parameter_values','texture_parameter_values'])
(root/'Receipts/cloud-sea-brown-diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('CLOUD_SEA_BROWN_DIAGNOSIS '+json.dumps(report))
