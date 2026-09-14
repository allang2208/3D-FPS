"""Read the reported map's ground and pus defaults without PIE or asset changes."""
import json
from pathlib import Path
import unreal as u

lib = u.MaterialEditingLibrary
def vec(v): return [v.x, v.y, v.z]
def material(m):
    if not m: return None
    row = {'path': m.get_path_name()}
    if isinstance(m, u.MaterialInstanceConstant):
        row['parent'] = material(m.get_editor_property('parent'))
        row['scalars'] = {str(n): lib.get_material_instance_scalar_parameter_value(m,n) for n in lib.get_scalar_parameter_names(m)}
    elif isinstance(m, u.Material):
        row['blend'] = str(m.get_editor_property('blend_mode'))
        row['outputs'] = {}
        for key in ('BASE_COLOR','OPACITY','OPACITY_MASK','WORLD_POSITION_OFFSET'):
            e = lib.get_material_property_input_node(m,getattr(u.MaterialProperty,'MP_'+key))
            row['outputs'][key] = e.get_name() if e else None
    return row

level=u.get_editor_subsystem(u.LevelEditorSubsystem)
level.load_level('/Game/GameMaps/DayNight_Lighting')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
records=[]
for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    if a.get_actor_label()!='Floor': continue
    c=a.static_mesh_component
    origin,extent=a.get_actor_bounds(False)
    row={'actor':a.get_path_name(),'location':vec(a.get_actor_location()),'scale':vec(a.get_actor_scale3d()),
         'bounds_origin':vec(origin),'bounds_extent':vec(extent), 'mesh':c.static_mesh.get_path_name(),
         'materials':[material(c.get_material(i)) for i in range(c.get_num_materials())], 'traces':[]}
    for complex_trace in (False,True):
        hits=u.SystemLibrary.line_trace_multi_for_objects(world,u.Vector(400,0,40),u.Vector(400,0,-85),
            [u.ObjectTypeQuery.OBJECT_TYPE_QUERY1,u.ObjectTypeQuery.OBJECT_TYPE_QUERY2],complex_trace,[],u.DrawDebugTrace.NONE,True)
        contact=[]
        for h in hits:
            fields=h.to_dict()
            contact.append({'point':vec(fields['impact_point']),'normal':vec(fields['impact_normal'])})
        row['traces'].append({'complex':complex_trace,'hits':contact})
    records.append(row)
cls=u.load_class(None,'/Script/FPSGAME.FatZombiePusPool')
defaults=u.get_default_object(cls)
surface=defaults.get_editor_property('surface')
flags={key:str(surface.get_editor_property(key)) for key in ('visible','hidden_in_game','render_in_main_pass','render_in_depth_pass','only_owner_see','owner_no_see','mobility','bounds_scale','use_attach_parent_bound')}
report={'floor':records,'pus_flags':flags,'pus_material':material(defaults.get_editor_property('pus_material'))}
out=Path('D:/FPS3D/FPSGAME/Saved/FatZombiePusVisibility/main_surface.json')
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('FAT_PUS_MAIN_SURFACE_RECORDED')
