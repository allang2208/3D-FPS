import unreal as u,json
from pathlib import Path
D='/Game/Monsters/RootCrown';ME=u.MaterialEditingLibrary
bp=u.load_asset(D+'/BP_RootCrownRigPreview');cdo=u.get_default_object(bp.generated_class())
mat=cdo.get_editor_property('slash_material');mesh=cdo.get_editor_property('visual_mesh')
report={'material':mat.get_path_name() if mat else None,'blueprint_material':str(cdo.get_editor_property('mesh').get_material(0)),
        'mesh_materials':[str(s.material_interface) for s in mesh.materials],
        'pie_active':bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),
        'dirty_target_packages':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith(D)]}
nodes={};pending=[ME.get_material_property_input_node(mat,p) for p in (u.MaterialProperty.MP_FRONT_MATERIAL,u.MaterialProperty.MP_BASE_COLOR)]
while pending:
    node=pending.pop()
    if not node or node.get_path_name() in nodes:continue
    children=[c for c in ME.get_inputs_for_material_expression(mat,node) if c]
    entry={'class':node.get_class().get_name(),'inputs':list(ME.get_material_expression_input_names(node)),'parents':[c.get_name() for c in children]}
    if isinstance(node,u.MaterialExpressionTextureSample):entry['texture']=str(node.get_editor_property('texture'))
    nodes[node.get_path_name()]=entry;pending.extend(children)
report['nodes']=nodes
report['textures']=[t.get_path_name() for t in ME.get_material_used_textures(mat)]
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report['runtime_instances']=[{'actor':a.get_path_name(),'material':str(a.get_editor_property('mesh').get_material(0))} for a in u.GameplayStatics.get_all_actors_of_class(world,u.RootCrownRigPreview)] if world else []
Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014/Reports/material_v2_before.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
