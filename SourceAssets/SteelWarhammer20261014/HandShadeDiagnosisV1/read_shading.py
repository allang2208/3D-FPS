"""Read material bindings and the existing player/light state without changing it."""
from pathlib import Path
import json,unreal as u
P=Path(__file__).resolve().parent
def path(x):return x.get_path_name() if x else None
def prop(x,n):
    try:
        v=x.get_editor_property(n)
        return v if isinstance(v,(str,int,float,bool)) else str(v)
    except Exception:return None
def materials(mesh):
    return [{'slot':str(s.material_slot_name),'material':path(s.material_interface)} for s in mesh.get_editor_property('materials')]
def component(c):
    mesh=c.get_skinned_asset() if isinstance(c,u.SkinnedMeshComponent) else None
    return {'name':c.get_name(),'class':c.get_class().get_name(),'asset':path(mesh),'position':str(c.get_world_location()),
        'properties':{n:prop(c,n) for n in ('visible','hidden_in_game','only_owner_see','owner_no_see','cast_shadow','cast_hidden_shadow','cast_contact_shadow','cast_dynamic_shadow','self_shadow_only','first_person_primitive_type','lighting_channels')},
        'materials':[path(c.get_material(i)) for i in range(c.get_num_materials())] if isinstance(c,u.MeshComponent) else []}
mesh=u.load_asset('/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1')
out={'asset':path(mesh),'saved_slots':materials(mesh),'materials':[],'players':[],'lights':[],
     'shadow_cvars':{n:u.SystemLibrary.get_console_variable_int_value(n) for n in ('r.Shadow.Virtual.Enable','r.RayTracing.Shadows','r.FirstPerson.Shadow.Virtual.Clipmap')},
     'dirty_content':[path(p) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
     'dirty_maps':[path(p) for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]}
for s in mesh.get_editor_property('materials'):
    m=s.material_interface
    row={'path':path(m),'parent':prop(m,'parent'),'scalar_overrides':prop(m,'scalar_parameter_values'),'vector_overrides':prop(m,'vector_parameter_values')}
    out['materials'].append(row)
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
out['existing_game_world']=path(w)
if w:
    for a in u.GameplayStatics.get_all_actors_of_class(w,u.Character):
        if not a.is_locally_controlled():continue
        out['players'].append({'actor':path(a),'components':[component(c) for c in a.get_components_by_class(u.MeshComponent)]})
    # The day/night lights are components of a manager BP, not ALight actors.
    for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
        for c in a.get_components_by_class(u.LightComponent):
            out['lights'].append({'actor':path(a),'component':path(c),'class':c.get_class().get_name(),'direction':str(c.get_forward_vector()),'intensity':prop(c,'intensity'),'cast_shadows':prop(c,'cast_shadows'),'cast_ray_traced_shadow':prop(c,'cast_ray_traced_shadow'),'contact_shadow_length':prop(c,'contact_shadow_length'),'lighting_channels':prop(c,'lighting_channels')})
(P/'shading_readback.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({'saved_slots':out['saved_slots'],'game_world':out['existing_game_world'],'player_count':len(out['players']),'light_count':len(out['lights']),'receipt':str(P/'shading_readback.json')}))
