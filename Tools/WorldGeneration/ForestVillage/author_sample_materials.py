"""Make a shared calibrated Sensei surface and the two local transition materials."""
from pathlib import Path
import os
import runpy
import unreal as u

L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
FOLDER = '/Game/ForestPathStudy/VillageRegion/SurfaceSample'
ROAD = '/Game/WorldGeneration/TemperateHills/EastRiverRoad/'
STUDY = '/Game/ForestPathStudy/Materials/MI_ForestPathForest'
P = u.MaterialProperty
ATTR = P.MP_MATERIAL_ATTRIBUTES


def save(obj):
    if not E.save_loaded_asset(obj,False):
        raise RuntimeError('Could not save '+obj.get_path_name())


def create(name, kind, factory):
    path=FOLDER+'/'+name
    if E.does_asset_exist(path): return u.load_asset(path)
    return u.AssetToolsHelpers.get_asset_tools().create_asset(name,FOLDER,kind,factory)


def duplicate(source,name):
    path=FOLDER+'/'+name
    if E.does_asset_exist(path): return u.load_asset(path)
    asset=E.duplicate_asset(source,path)
    if not asset: raise RuntimeError('Could not duplicate '+source)
    return asset


def wire(source,output,dest,pin):
    if not L.connect_material_expressions(source,output,dest,pin):
        raise RuntimeError('Could not wire '+str(pin)+' on '+dest.get_name())


def original_attributes(mat):
    if mat.get_editor_property('use_material_attributes'):
        return L.get_material_property_input_node(mat,ATTR),L.get_material_property_input_node_output_name(mat,ATTR)
    attrs=L.create_material_expression(mat,u.MaterialExpressionMakeMaterialAttributes)
    if not u.ForestVillageRegion.copy_gate_material_inputs(mat,attrs):
        raise RuntimeError('Could not retain village ground inputs')
    return attrs,''


def gate_layers(mat):
    # This strip has no riverbank and its forest litter comes from the sample
    # palette. Drop the redundant texture reads before combining the two sides.
    bypass={'HillRiver'+suffix:'A' for suffix in ('BaseColor','Normal','Roughness','AmbientOcclusion')}
    bypass.update({'ForestLitter'+suffix:'Base' for suffix in ('BaseColor','Normal','Roughness','AO')})
    nodes=L.get_material_expressions(mat)
    # The maintained gate has no dry stone crust or gravel deposits. Use the
    # existing earth channel for those fallback families on this strip only.
    for node in nodes:
        if not isinstance(node,(u.MaterialExpressionTextureObject,u.MaterialExpressionTextureSample)): continue
        tex=node.get_editor_property('texture')
        if not tex: continue
        name=tex.get_name()
        if not name.startswith(('T_LC_GroundDry_00A_','T_LC_MossyGravel_00A_')): continue
        suffix=name.split('_00A_')[-1]
        earth=u.load_asset('/Game/UnrealNormandy/Textures/T_LC_GroundSoilExcavated_00A_'+suffix)
        if not earth: raise RuntimeError('Missing matching earth channel '+suffix)
        node.set_editor_property('texture',earth)
    for target in nodes:
        key=bypass.get(target.get_editor_property('desc'))
        if key is None: continue
        inputs=dict(zip(map(str,L.get_material_expression_input_names(target)),L.get_inputs_for_material_expression(mat,target)))
        source=inputs[key]
        channel=L.get_input_node_output_name_for_material_expression(target,source) or ''
        for receiver in nodes:
            for name,value in zip(L.get_material_expression_input_names(receiver),L.get_inputs_for_material_expression(mat,receiver)):
                if value==target: wire(source,channel,receiver,str(name))


def wrapper(mat,fn,transition,mask_uv=3):
    marker='Forest Village R3 shared surface'
    existing=next((n for n in L.get_material_expressions(mat) if n.get_editor_property('desc')==marker),None)
    if existing:
        if transition:
            mask=L.get_inputs_for_material_expression(mat,existing)[2]
            uv=L.get_inputs_for_material_expression(mat,mask)[0]
            uv.set_editor_property('coordinate_index',mask_uv)
            save(mat)
        return
    call=L.create_material_expression(mat,u.MaterialExpressionMaterialFunctionCall)
    if not call.set_material_function(fn):
        raise RuntimeError('Missing surface function output')
    result=call
    if transition:
        old,pin=original_attributes(mat)
        if not old: raise RuntimeError('Missing original ground on '+mat.get_name())
        uv=L.create_material_expression(mat,u.MaterialExpressionTextureCoordinate)
        uv.set_editor_property('coordinate_index',mask_uv)
        mask=L.create_material_expression(mat,u.MaterialExpressionComponentMask)
        mask.set_editor_property('r',True)
        for key in ('g','b','a'): mask.set_editor_property(key,False)
        wire(uv,'',mask,'')
        result=L.create_material_expression(mat,u.MaterialExpressionBlendMaterialAttributes)
        wire(old,pin,result,'A')
        wire(call,'',result,'B')
        wire(mask,'',result,'Alpha')
    mat.set_editor_property('use_material_attributes',True)
    if not L.connect_material_property(result,'',ATTR): raise RuntimeError('Cannot bind surface')
    result.set_editor_property('desc',marker)
    errors=L.recompile_material(mat)
    if errors: raise RuntimeError(mat.get_name()+' '+str(errors))
    save(mat)


def build(source):
    E.make_directory(FOLDER+'/Terrain')
    rough=FOLDER+'/T_ForestSample_GrassRoughness'
    if not E.does_asset_exist(rough):
        task=u.AssetImportTask()
        task.filename=str(Path(source)/'T_ForestSample_GrassRoughness.png')
        task.destination_path=FOLDER
        task.automated=True
        task.save=False
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex=u.load_asset(rough)
    tex.set_editor_property('srgb',False)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DEFAULT)
    save(tex)
    palette=duplicate(ROAD+'MI_EastRiverRoad','MI_ForestSamplePalette')
    legacy=u.load_asset(ROAD+'MI_EastRiverRoad')
    # The Sensei functions sample these values through a Linear Color sampler.
    # Project-shared mask textures keep their original settings elsewhere.
    compatible={}
    for layer in 'ABC':
        for field in ('Roughness','Ambient Occlusion','Height'):
            key=field+' '+layer
            original=L.get_material_instance_texture_parameter_value(legacy,key)
            if original.get_editor_property('compression_settings')!=u.TextureCompressionSettings.TC_MASKS:
                continue
            linear=duplicate(original.get_path_name(),'T_Linear_'+original.get_name())
            linear.set_editor_property('srgb',False)
            linear.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DEFAULT)
            save(linear)
            L.set_material_instance_texture_parameter_value(palette,key,linear)
            compatible[key]=linear
    sample=u.load_asset(STUDY)
    for layer in ('A','C'):
        for parameter in ('Size ','Normal Strength '):
            key=parameter+layer
            value=L.get_material_instance_scalar_parameter_value(sample,key)
            L.set_material_instance_scalar_parameter_value(palette,key,value)
    L.set_material_instance_texture_parameter_value(palette,'Roughness B',tex)
    L.update_material_instance(palette)
    save(palette)
    fn=create('MF_ForestVillageSurface',u.MaterialFunction,u.MaterialFunctionFactoryNew())
    if not u.ForestVillageRegion.build_surface_function(palette,fn):
        raise RuntimeError('Could not extract the Sensei surface')
    if E.does_asset_exist('/Game/ForestPathStudy/VillageRegion/WildGrass/MF_HillsWildGrass'):
        runpy.run_path(str(Path(__file__).with_name('author_wild_grass.py')))['connect_sample_verge'](fn)
    L.update_material_function(fn)
    save(fn)
    core=create('M_ForestVillageSurface',u.Material,u.MaterialFactoryNew())
    wrapper(core,fn,False)
    fringe=duplicate(ROAD+'M_EastRoad_Sensei','M_ForestVillageFringe')
    wrapper(fringe,fn,True)
    # Keep the road instance's real overrides on the legacy side of the blend.
    edge=duplicate(ROAD+'MI_EastRiverRoad','MI_ForestVillageFringe')
    L.set_material_instance_parent(edge,fringe)
    for key,linear in compatible.items():
        L.set_material_instance_texture_parameter_value(edge,key,linear)
    L.update_material_instance(edge)
    save(edge)
    gate=duplicate('/Game/WorldGeneration/TemperateHills/PebbleShore/M_PebbleShoreGround','M_ForestVillageGateApron')
    gate_layers(gate)
    wrapper(gate,fn,True,6)
    return core,edge,gate


if __name__=='__main__':
    build(Path(os.environ['FPS_FOREST_REGION_SOURCE']))
