"""Keep directional fluid displacement and normals attached to rotated authored rooms."""
import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE='/Game/Dungeons/Routes20260922/Materials';E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve running play')
paths={}
for source,name in [('/Game/Dungeons/SlimeSheet20260922/Materials/M_PusConvergingSheet','M_RoutePusSheet'),('/Game/Dungeons/SlimeSheet20260922/Materials/M_PusConvergedDrops','M_RoutePusDrops'),('/Game/Dungeons/SlimeSheet20260922/Materials/M_PusSingleImpact','M_RoutePusImpact'),('/Game/Dungeons/CombatExpansion20260922/Materials/M_PusFluidV2','M_RoutePusChannel')]:
    path=BASE+'/'+name;mat=u.load_asset(path)
    if not mat:mat=E.duplicate_asset(source,path)
    for prop in [u.MaterialProperty.MP_NORMAL,u.MaterialProperty.MP_WORLD_POSITION_OFFSET]:
        original=L.get_material_property_input_node(u.load_asset(source),prop)
        code=original.get_editor_property('code')
        src=next(e for e in L.get_material_expressions(mat) if isinstance(e,u.MaterialExpressionCustom) and (e.get_editor_property('code')==code or (prop==u.MaterialProperty.MP_NORMAL and e.get_editor_property('code').startswith('// DungeonPerformance.Analytic'))))
        n=L.get_material_property_input_node(mat,prop)
        if not isinstance(n,u.MaterialExpressionTransform):
            n=L.create_material_expression(mat,u.MaterialExpressionTransform)
        n.set_editor_property('transform_source_type',u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL)
        n.set_editor_property('transform_type',u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        if not L.connect_material_expressions(src,'',n,''):raise RuntimeError('Cannot wire local vector')
        L.connect_material_property(n,'',prop)
        if prop==u.MaterialProperty.MP_NORMAL:
            for expression in L.get_material_expressions(mat):
                if isinstance(expression,u.MaterialExpressionCustom) and 'pow(1-saturate(dot(N,V))' in expression.get_editor_property('code'):
                    L.connect_material_expressions(n,'',expression,'N')
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Save '+path)
    paths[name]=path
for source,name,parent in [('/Game/Dungeons/SlimeSheet20260922/Materials/MI_PusPuddleSingleImpact','MI_RoutePusPuddle','M_RoutePusImpact'),('/Game/Dungeons/CombatExpansion20260922/Materials/MI_PusChannelFluid','MI_RoutePusChannel','M_RoutePusChannel')]:
    path=BASE+'/'+name;mi=u.load_asset(path) or E.duplicate_asset(source,path);L.set_material_instance_parent(mi,u.load_asset(paths[parent]));L.update_material_instance(mi)
    if not E.save_loaded_asset(mi,False):raise RuntimeError('Save '+path)
    paths[name]=path
(ROOT/'Receipts/fluid-materials.json').write_text(json.dumps(paths,indent=2))
print('ROUTE_FLUID_MATERIALS_SAVED',len(paths))
