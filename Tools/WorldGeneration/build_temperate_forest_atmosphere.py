"""Author only the hills' wind/fog assets. Never rebuild or save the map.

Run after the Editor native build using the serialized background wrapper.
The species builder reapplies this layer after updating imported vegetation.
"""
import json
import runpy
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/TemperateForestAtmosphere20261110'
BASE='/Game/WorldGeneration/TemperateHills'
DEST=BASE+'/Atmosphere20261110'
SPECIES=BASE+'/ForestSpecies20261110'
LIB=u.MaterialEditingLibrary
EAL=u.EditorAssetLibrary
AT=u.AssetToolsHelpers.get_asset_tools()
REPORT={'saved':[], 'wind_profiles':{}, 'graph_connections':[], 'map_modified':False,
        'game_run':False, 'visual_tested':False, 'performance_tested':False}
TAG='ForestAtmosphere20261110V1'
understory=runpy.run_path(str(PROJECT/'Tools/WorldGeneration/temperate_understory_wind.py'))

def load(path):
    obj=u.load_asset(path)
    if not obj: raise RuntimeError('Missing forest asset: '+path)
    return obj

def backup(obj):
    package=obj.get_path_name().split('.')[0]
    if not package.startswith(BASE+'/'):raise RuntimeError('Outside hills ownership: '+package)
    relative=package.removeprefix('/Game/')
    for suffix in ('.uasset','.uexp','.ubulk'):
        src=PROJECT/'Content'/(relative+suffix)
        dst=ROOT/'Backups/Content'/(relative+suffix)
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(src,dst)

def save(obj):
    if not EAL.save_loaded_asset(obj,False):raise RuntimeError('Save failed: '+obj.get_path_name())
    REPORT['saved'].append(obj.get_path_name())

def asset(name,cls,factory):
    path=DEST+'/'+name
    obj=u.load_asset(path) if EAL.does_asset_exist(path) else AT.create_asset(name,DEST,cls,factory)
    if not obj:raise RuntimeError('Could not create '+path)
    backup(obj)
    return obj

def expression(mat,cls):
    node=LIB.create_material_expression(mat,cls)
    node.set_editor_property('desc',TAG)
    return node

def wire(source,target,pin,out=''):
    if not LIB.connect_material_expressions(source,out,target,pin):
        raise RuntimeError('Wind material pin: '+pin)

def shrub_material(mpc):
    path=DEST+'/M_ForestShrubWind'
    mat=load(path) if EAL.does_asset_exist(path) else AT.duplicate_asset('M_ForestShrubWind',DEST,load(SPECIES+'/Materials/M_ForestPCG'))
    backup(mat)
    uses_attributes=mat.get_editor_property('use_material_attributes')
    original=LIB.get_material_property_input_node(mat,u.MaterialProperty.MP_MATERIAL_ATTRIBUTES) if uses_attributes else None
    original_output=LIB.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_MATERIAL_ATTRIBUTES) if uses_attributes else ''
    if original and original.get_editor_property('desc')==TAG:
        wrapper=original
        original=LIB.get_inputs_for_material_expression(mat,wrapper)[0]
        output=LIB.get_input_node_output_name_for_material_expression(wrapper,original)
        original_output=output if isinstance(output,str) else output[-1] if output else ''
    for node in LIB.get_material_expressions(mat):
        if node.get_editor_property('desc')==TAG:LIB.delete_material_expression(mat,node)
    world=expression(mat,u.MaterialExpressionWorldPosition)
    world.set_editor_property('world_position_shader_offset',u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    # A single instance-space pivot and axis are shared by trunk and every
    # assembly leaf. Vertex-local ripples stretch the small, scaled-down leaves.
    roots=[]
    for xyz in ((0.,0.,0.),(0.,0.,1.)):
        constant=expression(mat,u.MaterialExpressionConstant3Vector)
        constant.set_editor_property('constant',u.LinearColor(*xyz,0.))
        point=expression(mat,u.MaterialExpressionTransformPosition)
        point.set_editor_property('transform_source_type',u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE)
        point.set_editor_property('transform_type',u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
        wire(constant,point,LIB.get_material_expression_input_names(point)[0])
        roots.append(point)
    wind=expression(mat,u.MaterialExpressionCollectionParameter)
    wind.set_editor_property('collection',mpc)
    wind.set_editor_property('parameter_name','ForestWind')
    time=expression(mat,u.MaterialExpressionTime)
    strength=expression(mat,u.MaterialExpressionScalarParameter)
    strength.set_editor_property('parameter_name','ForestSwayDegrees')
    strength.set_editor_property('default_value',.45)
    sway=expression(mat,u.MaterialExpressionCustom)
    sway.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    sway.set_editor_property('code',understory['SHRUB_SWAY'])
    inputs={'WorldPos':world,'RootWorld':roots[0],'UpWorld':roots[1],'Wind':wind,'Time':time,'Strength':strength}
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    sway.set_editor_property('inputs',pins)
    for name,node in inputs.items():wire(node,sway,name)
    if uses_attributes:
        if original is None:raise RuntimeError('Forest surface attributes are missing')
        wrapper=expression(mat,u.MaterialExpressionSetMaterialAttributes)
        # The protected input array cannot be authored from Python. The native
        # public pin API updates it together with the attribute ID, without UI.
        index=u.TemperateForestAuthoringLibrary.add_wind_offset_pin(wrapper)
        if index<0:raise RuntimeError('Cannot create the forest WPO attribute pin')
        names=LIB.get_material_expression_input_names(wrapper)
        wire(original,wrapper,names[0],original_output)
        wire(sway,wrapper,names[index])
        if not LIB.connect_material_property(wrapper,'',u.MaterialProperty.MP_MATERIAL_ATTRIBUTES):
            raise RuntimeError('Cannot connect forest surface attributes')
    elif not LIB.connect_material_property(sway,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET):
        raise RuntimeError('Cannot connect shrub WPO')
    REPORT['shrub_wind_material_attributes']=uses_attributes
    mat.set_editor_property('max_world_position_offset_displacement',8.)
    LIB.recompile_material(mat)
    save(mat)
    # Keep the same rigid rotation on wood and foliage. The 8 cm material bound
    # exceeds the <= 4 cm offset of the authored 0.7-2.4 m hills shrubs.
    for name in ('MI_Common_Hazel_Bark_01','MI_Common_Hazel_Foliage_01'):
        mi=load(SPECIES+'/Materials/'+name);backup(mi)
        LIB.set_material_instance_parent(mi,mat)
        LIB.set_material_instance_scalar_parameter_value(mi,'ForestSwayDegrees',.45)
        LIB.update_material_instance(mi);save(mi)
    REPORT['shrub_wind']={'mode':'rigid_root_rotation','degrees':.45,'max_degrees':.65,
                          'max_weather_amplitude':1.1,'material_wpo_limit_cm':8.,
                          'vertex_ripple':False,'phase_source':'instance_root_world_position'}

def plant_profile(mesh,role):
    if role=='forest_ferns':
        backup(mesh)
        understory['fern_profile'](mesh)
        REPORT['wind_profiles'][mesh.get_path_name()]={'role':role,'gust_attenuation':.94}
        save(mesh)
        return
    data=next((d for d in mesh.get_editor_property('asset_user_data')
               if d and d.get_class().get_name()=='DynamicWindSkeletalData'),None)
    if data is None:raise RuntimeError('Imported wind skeleton data missing: '+mesh.get_path_name())
    if EAL.get_metadata_tag(mesh,TAG):
        REPORT['wind_profiles'][mesh.get_path_name()]={'role':role,'previously_authored':True}
        return
    backup(mesh)
    groups=list(data.get_editor_property('SimulationGroups'))
    before=[g.export_text() for g in groups]
    # Retain imported bone assignments, zero root weights and dual influences.
    for group in groups:
        trunk=group.get_editor_property('bIsTrunkGroup')
        scale=(.62 if trunk else .78) if role=='forest_saplings' else (.60 if trunk else .85)
        for key in ('Influence','MinInfluence','MaxInfluence'):
            group.set_editor_property(key,group.get_editor_property(key)*scale)
    data.set_editor_property('SimulationGroups',groups)
    data.set_editor_property('bIsEnabled',True)
    data.set_editor_property('bIsGroundCover',False)
    data.set_editor_property('GustAttenuation',.55 if role=='forest_saplings' else .65)
    EAL.set_metadata_tag(mesh,TAG,role)
    REPORT['wind_profiles'][mesh.get_path_name()]={'role':role,'before':before,'after':[g.export_text() for g in groups]}
    save(mesh)

def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor.get_game_world():raise RuntimeError('Do not author forest assets during PIE')
    dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name().startswith(BASE+'/')]
    if dirty:raise RuntimeError('Preserve unsaved hills edits: '+repr(dirty))
    if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower():
        u.SystemLibrary.execute_console_command(editor.get_editor_world(),'Editor.AsyncStaticMeshCompilation 0')
    da=load(BASE+'/DA_TemperateHillsStreaming');backup(da)
    # Small, hard-referenced assets travel with the biome data; no Tick-time loads.
    mpc=asset('MPC_ForestWind',u.MaterialParameterCollection,u.MaterialParameterCollectionFactoryNew())
    parameters=list(mpc.get_editor_property('vector_parameters'))
    param=next((v for v in parameters if str(v.get_editor_property('parameter_name'))=='ForestWind'),None)
    if param is None:
        param=u.CollectionVectorParameter();param.set_editor_property('parameter_name','ForestWind');parameters.append(param)
    param.set_editor_property('default_value',u.LinearColor(-1.,0.,.492,0.))
    # Struct array elements copy on read; replace the matching element explicitly.
    parameters=[param if str(v.get_editor_property('parameter_name'))=='ForestWind' else v for v in parameters]
    mpc.set_editor_property('vector_parameters',parameters);save(mpc)
    factory=u.new_object(u.load_class(None,'/Script/DynamicWindEditor.DynamicWindDataFactory'))
    provider=asset('DA_ForestDynamicWind',u.DynamicWindData,factory);save(provider)
    for role in ('trees','forest_saplings','forest_ferns'):
        for soft in da.get_editor_property(role):plant_profile(load(soft.get_path_name()),role)
    for name in ('PCG_BlackPoplar','PCG_HillsShrubs'):
        graph=load(BASE+'/'+name);backup(graph)
        for node in graph.get_editor_property('nodes'):
            settings=node.get_settings()
            cls=settings.get_class().get_name()
            if cls=='PCGSkinnedMeshSpawnerSettings':
                selector=settings.get_editor_property('mesh_selector_parameters')
                descriptor=selector.get_editor_property('template_descriptor')
                descriptor.set_editor_property('transform_provider',provider)
                selector.set_editor_property('template_descriptor',descriptor)
                REPORT['graph_connections'].append(graph.get_path_name())
            elif cls=='PCGStaticMeshSpawnerSettings' and name=='PCG_HillsShrubs':
                selector=settings.get_editor_property('mesh_selector_parameters')
                descriptor=selector.get_editor_property('template_descriptor')
                descriptor.set_editor_property('world_position_offset_disable_distance',9000)
                selector.set_editor_property('template_descriptor',descriptor)
        save(graph)
    shrub_material(mpc)
    fog=load(BASE+'/MI_ValleyLowFog');backup(fog)
    for key,value in {'FogOverallDensity':.20,'BaseFogContrast':1.65,'DetailFogContrast':1.75,
                      'BaseFogIntensity':.55,'DetailFogIntensity':.45,'Distance':900.,'EmissiveIntensity':0.}.items():
        LIB.set_material_instance_scalar_parameter_value(fog,key,value)
    LIB.update_material_instance(fog);save(fog)
    da.set_editor_property('valley_fog_density',.20)
    da.set_editor_property('river_mist_density',.14)
    da.set_editor_property('forest_wind_parameters',mpc)
    da.set_editor_property('forest_wind_provider',provider)
    save(da)
    visibility=runpy.run_path(str(PROJECT/'Tools/WorldGeneration/fix_temperate_vegetation_visibility.py'),run_name='__main__')
    REPORT['saved'].extend(visibility['REPORT']['saved'])
    REPORT['finished_at']=datetime.now().astimezone().isoformat()
    (ROOT/'Receipts/assets.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
    u.log('FOREST_ATMOSPHERE_SAVED '+str(len(REPORT['saved'])))

if __name__=='__main__':main()
