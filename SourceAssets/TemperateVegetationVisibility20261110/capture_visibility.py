"""Read hills PCG visibility settings and mesh/material bounds; no game or saves."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/TemperateVegetationVisibility20261110')
BASE='/Game/WorldGeneration/TemperateHills'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():raise RuntimeError('Do not alter a running play world')
commandlet='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if commandlet:
    u.SystemLibrary.execute_console_command(editor.get_editor_world(),'Editor.AsyncStaticMeshCompilation 0')
    u.SystemLibrary.execute_console_command(editor.get_editor_world(),'Editor.AsyncSkinnedAssetCompilation 0')
    u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_TemperateHills_Initial')
result={'world':editor.get_editor_world().get_path_name(),'actors':[],'graphs':{},'meshes':{},'materials':{}}
def read(obj,fields):
    out={}
    for field in fields:
        try:out[field]=str(obj.get_editor_property(field))
        except Exception:pass
    return out
for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    if isinstance(actor,u.TemperateHillsWorld):
        row={'path':actor.get_path_name(),'position':str(actor.get_actor_location()),'layers':[]}
        for c in actor.get_components_by_class(u.PCGComponent):
            d=read(c,('generation_trigger','is_component_partitioned','generation_radii','override_generation_radii'))
            d['name']=c.get_name()
            policy=c.get_editor_property('scheduling_policy')
            d['policy']=read(policy,('use_frustum_culling','use_distance','use_direction','direction_weight','generate_bounds_modifier','cleanup_bounds_modifier','network_mode')) if policy else None
            row['layers'].append(d)
        result['actors'].append(row)
da=u.load_asset(BASE+'/DA_TemperateHillsStreaming')
for soft in da.get_editor_property('graphs'):
    g=u.load_asset(soft.get_path_name())
    row=read(g,('use_2d_grid','hi_gen_grid_size','enable_hierarchical_generation'))
    row['spawners']=[]
    for node in g.get_editor_property('nodes'):
        s=node.get_settings()
        if 'SpawnerSettings' not in s.get_class().get_name():continue
        selector=s.get_editor_property('mesh_selector_parameters')
        try:
            d=selector.get_editor_property('template_descriptor')
            row['spawners'].append({'class':s.get_class().get_name(),'descriptor':d.export_text()})
        except Exception as ex:row['spawners'].append(str(ex))
    result['graphs'][g.get_path_name()]=row
for role in ('trees','forest_saplings','forest_ferns','shrubs','grass','grass_accents','meadow_flowers'):
    for soft in da.get_editor_property(role):
        m=u.load_asset(soft.get_path_name())
        row=read(m,('positive_bounds_extension','negative_bounds_extension','nanite_settings','lod_for_collision'))
        row.update({'role':role,'bounds':str(m.get_bounds())})
        result['meshes'][m.get_path_name()]=row
        slots=m.get_editor_property('materials' if isinstance(m,u.SkeletalMesh) else 'static_materials')
        for slot in slots:
            mat=slot.get_editor_property('material_interface')
            while mat and mat.get_path_name() not in result['materials']:
                info=read(mat,('parent','use_material_attributes','max_world_position_offset_displacement','opacity_mask_clip_value','blend_mode'))
                if isinstance(mat,u.MaterialInstanceConstant):
                    info['switches']={str(p):u.MaterialEditingLibrary.get_material_instance_static_switch_parameter_value(mat,p) for p in u.MaterialEditingLibrary.get_static_switch_parameter_names(mat) if any(t in str(p).lower() for t in ('wind','fade','bend','distance'))}
                elif isinstance(mat,u.Material):
                    info['nodes']=[{'class':n.get_class().get_name(),**read(n,('desc','code','parameter_name','default_value'))} for n in u.MaterialEditingLibrary.get_material_expressions(mat) if any(t in n.get_class().get_name() for t in ('Custom','Fade','Position','Bounds','FunctionCall'))]
                result['materials'][mat.get_path_name()]=info
                mat=mat.get_editor_property('parent') if isinstance(mat,u.MaterialInstanceConstant) else None
(ROOT/'Receipts/visibility-inputs.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
u.log('HILLS_VISIBILITY_INPUTS_READ')
