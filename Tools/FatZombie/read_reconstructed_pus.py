"""Reconstruct the recorded residue for data diagnosis without starting PIE."""
import unreal as u
import json
from pathlib import Path
lib = u.MaterialEditingLibrary
mat = u.load_asset('/Game/Monsters/FatZombieMeshy/Pus/M_FatZombie_Pus')
report = {'properties': {}, 'mask': {}}
for key in ('use_material_attributes', 'two_sided', 'material_domain', 'blend_mode', 'disable_depth_test'):
    report['properties'][key] = str(mat.get_editor_property(key))
mask = lib.get_material_property_input_node(mat, u.MaterialProperty.MP_OPACITY_MASK)
report['mask']['class'] = mask.get_class().get_name()
report['mask']['input_names'] = [str(n) for n in lib.get_material_expression_input_names(mask)]
report['mask']['sources'] = [n.get_name() if n else None for n in lib.get_inputs_for_material_expression(mat, mask)]
Path('D:/FPS3D/FPSGAME/Saved/FatZombiePusVisibility/active_mask.json').write_text(json.dumps(report, indent=2))
floor_mat = u.load_asset('/Engine/OpenWorldTemplate/LandscapeMaterial/M_ProcGrid')
floor_graph = {'attributes': str(floor_mat.get_editor_property('use_material_attributes')), 'expressions': []}
for e in lib.get_material_expressions(floor_mat):
    r={'name':e.get_name(),'class':e.get_class().get_name(),'pins':[str(n) for n in lib.get_material_expression_input_names(e)],
       'inputs':[n.get_name() if n else None for n in lib.get_inputs_for_material_expression(floor_mat,e)]}
    if isinstance(e,u.MaterialExpressionMaterialFunctionCall): r['function']=str(e.get_editor_property('material_function'))
    floor_graph['expressions'].append(r)
Path('D:/FPS3D/FPSGAME/Saved/FatZombiePusVisibility/floor_graph.json').write_text(json.dumps(floor_graph, indent=2))
u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GameMaps/DayNight_Lighting')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    if actor.get_actor_label() == 'Floor':
        print('FAT_PUS_EDITOR_FLOOR',actor.get_path_name(),str(actor.get_actor_bounds(False)))
        u.load_asset('/Engine/OpenWorldTemplate/LandscapeMaterial/MI_ProcGrid')
for x,y in ((400,0),(-353.966559,638.393534)):
    hits=u.SystemLibrary.line_trace_multi_for_objects(world,u.Vector(x,y,40),u.Vector(x,y,-85),
        [u.ObjectTypeQuery.OBJECT_TYPE_QUERY1,u.ObjectTypeQuery.OBJECT_TYPE_QUERY2],False,[],u.DrawDebugTrace.NONE,True)
    print('FAT_PUS_TRACE',x,y,[str(h.to_dict()) for h in (hits or [])])
u.SystemLibrary.execute_console_command(world,'fps.InspectFatZombiePus')
