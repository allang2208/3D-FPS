"""Align saved PCG culling with the native hills streaming contract.

Only owned material/graph packages are saved. No map load, play or rendering.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/TemperateVegetationVisibility20261110'
BASE='/Game/WorldGeneration/TemperateHills'
LIB=u.MaterialEditingLibrary
EAL=u.EditorAssetLibrary
TAG='HillsVisibility20261110'
GRASS_TAG=TAG+'GrassDither'
REPORT={'saved':[],'distances_cm':{},'before':{},'map_modified':False,'game_run':False,'visual_tested':False}
GRAPHS=('PCG_BlackPoplar','PCG_HillsRocks','PCG_HillsShrubs','PCG_HillsGrass')
TREES=('M_BlackPoplarPCG','ForestSpecies20261110/Materials/M_ForestPCG')

def load(path):
    obj=u.load_asset(path)
    if obj is None:raise RuntimeError('Missing owned forest asset: '+path)
    return obj

def backup(obj):
    path=obj.get_path_name().split('.')[0]
    if not path.startswith(BASE+'/'):raise RuntimeError('Outside hills ownership: '+path)
    for suffix in ('.uasset','.uexp','.ubulk'):
        relative=path.removeprefix('/Game/')+suffix
        source=PROJECT/'Content'/relative
        target=ROOT/'Backups/Content'/relative
        if source.exists() and not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)

def save(obj):
    if not EAL.save_loaded_asset(obj,False):raise RuntimeError('Save failed: '+obj.get_path_name())
    REPORT['saved'].append(obj.get_path_name())

def node(mat,cls,marker=TAG):
    n=LIB.create_material_expression(mat,cls)
    n.set_editor_property('desc',marker)
    return n

def wire(source,target,pin='',output=''):
    if not LIB.connect_material_expressions(source,output,target,pin):raise RuntimeError('Visibility material pin: '+pin)

def dither(mat,amount,marker=TAG):
    n=node(mat,u.MaterialExpressionMaterialFunctionCall,marker)
    n.set_editor_property('material_function',load('/Engine/Functions/Engine_MaterialFunctions02/Utility/DitherTemporalAA'))
    wire(amount,n,LIB.get_material_expression_input_names(n)[0])
    return n

def distance_fade(mat,distances):
    backup(mat)
    if not mat.get_editor_property('use_material_attributes'):
        raise RuntimeError('Expected PVE tree attributes: '+mat.get_path_name())
    prop=u.MaterialProperty.MP_MATERIAL_ATTRIBUTES
    original=LIB.get_material_property_input_node(mat,prop)
    output=LIB.get_material_property_input_node_output_name(mat,prop)
    if original and original.get_editor_property('desc')==TAG:
        wrapper=original
        original=LIB.get_inputs_for_material_expression(mat,wrapper)[0]
        result=LIB.get_input_node_output_name_for_material_expression(wrapper,original)
        output=result if isinstance(result,str) else result[-1] if result else ''
    if original is None:raise RuntimeError('Tree surface attributes missing')
    for n in list(LIB.get_material_expressions(mat)):
        if n.get_editor_property('desc')==TAG:LIB.delete_material_expression(mat,n)
    get=node(mat,u.MaterialExpressionGetMaterialAttributes)
    mask_index=u.TemperateForestAuthoringLibrary.add_visibility_mask_pin(get)
    if mask_index<0:raise RuntimeError('Cannot read the tree opacity attribute')
    wire(original,get,LIB.get_material_expression_input_names(get)[0],output)
    mask_output=LIB.get_material_expression_output_names(get)[mask_index]
    position=node(mat,u.MaterialExpressionWorldPosition)
    position.set_editor_property('world_position_shader_offset',u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    camera=node(mat,u.MaterialExpressionCameraPositionWS)
    start=node(mat,u.MaterialExpressionScalarParameter)
    start.set_editor_property('parameter_name','HillsVisibilityFadeStartCm')
    start.set_editor_property('default_value',distances.x)
    end=node(mat,u.MaterialExpressionScalarParameter)
    end.set_editor_property('parameter_name','HillsVisibilityFadeEndCm')
    end.set_editor_property('default_value',distances.y)
    fade=node(mat,u.MaterialExpressionCustom)
    fade.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
    # Nanite does not populate the ordinary PerInstanceFadeAmount path. Use a
    # bounded world-space band for both Nanite skinned and fallback tree passes.
    fade.set_editor_property('code','return 1.0 - smoothstep(Start, max(Start + 1.0, End), distance(Position, Camera));')
    inputs={'Position':position,'Camera':camera,'Start':start,'End':end}
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    fade.set_editor_property('inputs',pins)
    for name,value in inputs.items():wire(value,fade,name)
    mask=node(mat,u.MaterialExpressionMultiply)
    wire(get,mask,'A',mask_output)
    wire(dither(mat,fade),mask,'B')
    put=node(mat,u.MaterialExpressionSetMaterialAttributes)
    index=u.TemperateForestAuthoringLibrary.add_visibility_mask_pin(put)
    if index<0:raise RuntimeError('Cannot write the tree opacity attribute')
    names=LIB.get_material_expression_input_names(put)
    wire(original,put,names[0],output);wire(mask,put,names[index])
    if not LIB.connect_material_property(put,'',prop):raise RuntimeError('Cannot connect the tree attributes')
    LIB.recompile_material(mat);save(mat)

def grass_fade():
    mat=load(BASE+'/Grass/M_TemperateMeadow');backup(mat)
    root=LIB.get_material_property_input_node(mat,u.MaterialProperty.MP_OPACITY_MASK)
    if not root or root.get_editor_property('desc')!='TemperateMeadowDistanceFade':
        raise RuntimeError('Preserve the unknown grass opacity graph')
    existing=next((n for n in LIB.get_material_expressions(mat) if n.get_editor_property('desc')==GRASS_TAG),None)
    if existing is None:
        inputs=LIB.get_inputs_for_material_expression(mat,root)
        amount=inputs[1]
        if not isinstance(amount,u.MaterialExpressionPerInstanceFadeAmount):
            raise RuntimeError('Preserve the unknown grass distance fade')
        wire(dither(mat,amount,GRASS_TAG),root,'B')
    LIB.recompile_material(mat);save(mat)

def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor.get_game_world():raise RuntimeError('Do not save visibility assets during PIE')
    owned={BASE+'/'+n for n in (*GRAPHS,*TREES,'Grass/M_TemperateMeadow')}
    conflicts=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in owned]
    if conflicts:raise RuntimeError('Preserve unsaved forest changes: '+repr(conflicts))
    distances=[u.TemperateForestAuthoringLibrary.get_visibility_distances(i) for i in range(5)]
    for i,d in enumerate(distances):REPORT['distances_cm'][str(i)]={'fade_start':d.x,'visible_end':d.y,'generate':d.z,'cleanup':d.z*1.3}
    for layer,name in enumerate(GRAPHS):
        graph=load(BASE+'/'+name);backup(graph)
        REPORT['before'][name]=[]
        for n in graph.get_editor_property('nodes'):
            settings=n.get_settings()
            cls=settings.get_class().get_name()
            if cls not in ('PCGSkinnedMeshSpawnerSettings','PCGStaticMeshSpawnerSettings'):continue
            role=4 if layer==2 and cls=='PCGSkinnedMeshSpawnerSettings' else layer
            selector=settings.get_editor_property('mesh_selector_parameters')
            desc=selector.get_editor_property('template_descriptor')
            REPORT['before'][name].append({'class':cls,'start':desc.get_editor_property('instance_start_cull_distance'),'end':desc.get_editor_property('instance_end_cull_distance')})
            desc.set_editor_property('instance_start_cull_distance',int(distances[role].x))
            desc.set_editor_property('instance_end_cull_distance',int(distances[role].y))
            selector.set_editor_property('template_descriptor',desc)
        save(graph)
    for name in TREES:distance_fade(load(BASE+'/'+name),distances[0])
    grass_fade()
    REPORT['finished_at']=datetime.now().astimezone().isoformat()
    (ROOT/'Receipts/visibility-saved.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
    u.log('HILLS_VISIBILITY_SAVED '+str(len(REPORT['saved'])))

if __name__=='__main__':main()
