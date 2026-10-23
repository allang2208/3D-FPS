"""Repair the missing fabric color pin in source and worn materials, preserving WPO."""
import json,shutil,hashlib
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BackpackMotion20261022/FabricRepair';R.mkdir(exist_ok=True)
paths=['/Game/Characters/ExpeditionBackpack20261022/M_ExpeditionHarness_Fabric',
       '/Game/Characters/BackpackMotion20261022/Materials/M_Motion_M_ExpeditionHarness_Fabric_b63f8c']
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection(paths):raise RuntimeError('A target fabric material has unsaved editor edits')
rows=[]
for path in paths:
    mat=u.load_asset(path)
    if not mat:raise RuntimeError('Missing target '+path)
    source=P/'Content'/(path.removeprefix('/Game/')+'.uasset');backup=R/'Before'/source.name
    backup.parent.mkdir(exist_ok=True)
    if not backup.exists():shutil.copy2(source,backup)
    expressions=L.get_material_expressions(mat)
    gray=next(n for n in expressions if isinstance(n,u.MaterialExpressionDesaturation))
    color=next(n for n in expressions if isinstance(n,u.MaterialExpressionTextureSample)
               and n.get_editor_property('texture') and n.get_editor_property('texture').get_name()=='T_HarnessFabricR1_BaseColor')
    fraction=next(n for n in expressions if isinstance(n,u.MaterialExpressionConstant) and n.get_editor_property('r')==1.)
    before=[n.get_name() if n else None for n in L.get_inputs_for_material_expression(mat,gray)]
    pins=[str(n) for n in L.get_material_expression_input_names(gray)]
    wpo=L.get_material_property_input_node(mat,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    surface={name:L.get_material_property_input_node(mat,prop) for name,prop in [
        ('BaseColor',u.MaterialProperty.MP_BASE_COLOR),('Normal',u.MaterialProperty.MP_NORMAL),
        ('Roughness',u.MaterialProperty.MP_ROUGHNESS),('Metallic',u.MaterialProperty.MP_METALLIC)]}
    if not L.connect_material_expressions(color,'RGB',gray,''):raise RuntimeError('Could not connect input zero')
    if not L.connect_material_expressions(fraction,'',gray,'Fraction'):raise RuntimeError('Could not connect fraction')
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Fabric compilation failed: '+str(errors))
    # GetStatistics finishes this material's compilation on the active RHI.
    # A NullRHI save alone cannot establish that SM6 has a usable shader map.
    stats=L.get_statistics(mat)
    vertex=stats.num_vertex_shader_instructions;pixel=stats.num_pixel_shader_instructions
    if vertex<=0 or pixel<=0:raise RuntimeError('Run this repair with a real RHI; no completed shader instructions were returned')
    after=[n.get_name() if n else None for n in L.get_inputs_for_material_expression(mat,gray)]
    if color.get_name() not in after:raise RuntimeError('Fabric color connection did not persist')
    if L.get_material_property_input_node(mat,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)!=wpo:
        raise RuntimeError('Motion connection changed unexpectedly')
    E.set_metadata_tag(mat,'ExpeditionFabricRepair','ConnectedColorInput0_20261022')
    if not (u.EditorLoadingAndSavingUtils.save_packages([mat.get_outer()],False) or E.save_loaded_asset(mat,False)):
        raise RuntimeError('Fabric material was not saved')
    rows.append({'material':path,'desaturation_pin_names':pins,'before_connected_nodes':before,'after_connected_nodes':after,
                 'color_texture':color.get_editor_property('texture').get_path_name(),'wpo_preserved':True,
                 'surface_roots':{name:n.get_name() if n else None for name,n in surface.items()},
                 'vertex_shader_instructions':vertex,'pixel_shader_instructions':pixel,'saved':True,
                 'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
    print('EXPEDITION_FABRIC_REPAIRED',path,vertex,pixel,flush=True)
(R/'saved.json').write_text(json.dumps({'cause':'missing Desaturation color input, SM6 fallback material','materials':rows,
    'material_compilation_checked':True,'gameplay_tested':False,'rendered_preview':False},indent=2))
print('EXPEDITION_FABRIC_REPAIR_COMPLETE',flush=True)
