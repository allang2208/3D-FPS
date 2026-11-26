"""Clone only the two body variants' surfaces and add continuous crouch lift."""
import hashlib,importlib.util,json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/RangerCrouchFit20261021';DEST='/Game/Characters/ModularOutfit20260924/RangerCrouchFit20261021/Materials'
spec=importlib.util.spec_from_file_location('ranger_pose_clearance',str(P/'Tools/RangerCrouchFit/pose_clearance.py'));recipe=importlib.util.module_from_spec(spec);spec.loader.exec_module(recipe)
CODE=recipe.HLSL;REV=hashlib.sha256(CODE.encode()+Path(__file__).read_bytes()).hexdigest();E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary;cache={}
def node(mat,kind,**props):
    n=L.create_material_expression(mat,kind)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(source,target,pin,output=''):
    if not L.connect_material_expressions(source,output,target,pin):raise RuntimeError('Ranger crouch material wire '+pin)
def first(n):return str(L.get_material_expression_input_names(n)[0])
def make(source):
    original=source.get_path_name()
    if original in cache:return cache[original]
    suffix=hashlib.sha256((original+REV).encode()).hexdigest()[:12];path=DEST+'/'+('MI_' if isinstance(source,u.MaterialInstanceConstant) else 'M_')+'RangerCrouch_'+suffix
    result=u.load_asset(path)
    if result and E.get_metadata_tag(result,'RangerCrouchShader')==REV:cache[original]=result;return result
    result=result or E.duplicate_asset(original,path)
    if not result:raise RuntimeError('Cannot clone '+original)
    if isinstance(result,u.MaterialInstanceConstant):L.set_material_instance_parent(result,make(source.get_editor_property('parent')))
    elif isinstance(result,u.Material):
        attrs=result.get_editor_property('use_material_attributes');prop=u.MaterialProperty.MP_MATERIAL_ATTRIBUTES if attrs else u.MaterialProperty.MP_WORLD_POSITION_OFFSET
        previous=L.get_material_property_input_node(result,prop);pin=L.get_material_property_input_node_output_name(result,prop) if previous else ''
        if attrs:
            get=node(result,u.MaterialExpressionGetMaterialAttributes);idx=u.FPSModularOutfitComponent.add_robe_hem_offset_pin(get)
            if idx<0:raise RuntimeError('Cannot read source material offset')
            wire(previous,get,first(get),pin);old,old_pin=get,str(L.get_material_expression_output_names(get)[idx])
        elif previous:old,old_pin=previous,pin
        else:old,old_pin=node(result,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,0,0)),''
        world=node(result,u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
        local=node(result,u.MaterialExpressionTransformPosition,transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL);wire(world,local,first(local))
        rest=node(result,u.MaterialExpressionPreSkinnedPosition)
        custom=node(result,u.MaterialExpressionCustom,description='Ranger crouch hem clearance',code=CODE,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
        inputs=[]
        for name in ('Rest','Skinned'):
            inp=u.CustomInput();inp.set_editor_property('input_name',name);inputs.append(inp)
        custom.set_editor_property('inputs',inputs);wire(rest,custom,'Rest');wire(local,custom,'Skinned')
        world_delta=node(result,u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD);wire(custom,world_delta,first(world_delta))
        total=node(result,u.MaterialExpressionAdd);wire(old,total,'A',old_pin);wire(world_delta,total,'B')
        if attrs:
            set_attrs=node(result,u.MaterialExpressionSetMaterialAttributes);idx=u.FPSModularOutfitComponent.add_robe_hem_offset_pin(set_attrs);names=L.get_material_expression_input_names(set_attrs)
            wire(previous,set_attrs,str(names[0]),pin);wire(total,set_attrs,str(names[idx]));output=set_attrs
        else:output=total
        if not L.connect_material_property(output,'',prop):raise RuntimeError('Cannot connect ranger hem clearance')
        L.set_base_material_usage(result,u.MaterialUsage.MATUSAGE_SKELETAL_MESH,True)
        errors=L.recompile_material(result)
        if errors:raise RuntimeError('Crouch material compile failed '+str(errors))
    else:raise RuntimeError('Unsupported ranger surface '+original)
    E.set_metadata_tag(result,'RangerCrouchShader',REV);E.set_metadata_tag(result,'RangerCrouchSource',original)
    if not E.save_loaded_asset(result,False):raise RuntimeError('Cannot save crouch surface '+path)
    cache[original]=result;return result
def receipt():
    (R/'materials.json').write_text(json.dumps(dict(completed=True,revision=REV,hlsl=CODE,materials={k:v.get_path_name() for k,v in cache.items()},scope='Jason and owner body surfaces only; native first-person arm materials unchanged',runtime_tested=False),indent=2),encoding='utf-8')
