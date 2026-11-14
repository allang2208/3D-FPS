import unreal as u
def apply(w,req):
    result={'lights':[],'geometry':[]}
    for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
        for c in a.get_components_by_class(u.LightComponent):
            row={'actor':a.get_actor_label(),'name':c.get_name(),'type':c.get_class().get_name(),'pos':c.get_world_location().to_tuple(),'rot':c.get_world_rotation().to_tuple()}
            for key in ['intensity','attenuation_radius','intensity_units','light_color','use_temperature','temperature','cast_shadows','indirect_lighting_intensity','inner_cone_angle','outer_cone_angle','source_width','source_height','light_function_material','max_draw_distance','max_distance_fade_range','light_falloff_exponent','use_inverse_squared_falloff']:
                try:
                    v=c.get_editor_property(key);row[key]=v if isinstance(v,(bool,int,float,str)) else str(v)
                except Exception:pass
            result['lights'].append(row)
        if a.get_actor_label().startswith(('Station','CartBay','OppositePlatform','CartUpper')):
            for c in a.get_components_by_class(u.StaticMeshComponent):
                if not c.static_mesh:continue
                result['geometry'].append({'label':a.get_actor_label(),'mesh':c.static_mesh.get_path_name(),'p':c.get_world_location().to_tuple(),'rot':c.get_world_rotation().to_tuple(),'s':c.get_world_scale().to_tuple(),'slots':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]})
    return result
