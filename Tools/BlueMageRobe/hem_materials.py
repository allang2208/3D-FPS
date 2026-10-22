"""Clone existing surface graphs/instances and add a draw-only hem envelope."""
import hashlib
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME')
DEST='/Game/Characters/ModularOutfit20260924/BlueMageRobe20261018/HemContinuity20261019/Materials'
CODE=(P/'Tools/BlueMageRobe/hem_conform.hlsl').read_text()
MASK_CODE=(P/'Tools/BlueMageRobe/hem_visibility.hlsl').read_text()
REV=hashlib.sha256(CODE.encode()+MASK_CODE.encode()+Path(__file__).read_bytes()).hexdigest()
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
cache={}

def node(mat,kind,**props):
    n=L.create_material_expression(mat,kind)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(source,target,pin,output=''):
    if not L.connect_material_expressions(source,output,target,pin):raise RuntimeError('Hem material connection failed: '+pin)
def first(n):return str(L.get_material_expression_input_names(n)[0])
def scalar(mat,name,value):return node(mat,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
def vector(mat,name,value=(0,0,0)):
    return node(mat,u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*value,1))

def make(source):
    if not source:raise RuntimeError('A hem layer must retain its original material')
    original=source.get_path_name()
    if original in cache:return cache[original]
    suffix=hashlib.sha256((original+REV).encode()).hexdigest()[:12]
    path=DEST+'/'+('MI_' if isinstance(source,u.MaterialInstanceConstant) else 'M_')+'RobeHem_'+suffix
    result=u.load_asset(path)
    if result and E.get_metadata_tag(result,'RobeHemShaderSHA')==REV:
        cache[original]=result;return result
    result=result or E.duplicate_asset(original,path)
    if not result:raise RuntimeError('Cannot duplicate surface '+original)
    if isinstance(result,u.MaterialInstanceConstant):
        L.set_material_instance_parent(result,make(source.get_editor_property('parent')))
        overrides=result.get_editor_property('base_property_overrides')
        overrides.set_editor_property('override_blend_mode',True)
        overrides.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
        result.set_editor_property('base_property_overrides',overrides)
    elif isinstance(result,u.Material):
        # Resume only after a fully saved graph, never insert a second envelope
        # over a partial earlier attempt in this task-owned material.
        marker='Robe hem continuous tuck'
        if any(isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('description'))==marker for n in L.get_material_expressions(result)):
            raise RuntimeError('Partial hem master needs a fresh revision: '+path)
        attrs=result.get_editor_property('use_material_attributes')
        was_masked=result.get_editor_property('blend_mode')==u.BlendMode.BLEND_MASKED
        original_mask=L.get_material_property_input_node(result,u.MaterialProperty.MP_OPACITY_MASK) if not attrs and was_masked else None
        mask_pin=L.get_material_property_input_node_output_name(result,u.MaterialProperty.MP_OPACITY_MASK) if original_mask else ''
        prop=u.MaterialProperty.MP_MATERIAL_ATTRIBUTES if attrs else u.MaterialProperty.MP_WORLD_POSITION_OFFSET
        original_node=L.get_material_property_input_node(result,prop)
        original_pin=L.get_material_property_input_node_output_name(result,prop) if original_node else ''
        if attrs:
            if not original_node:raise RuntimeError('Material attributes have no source '+original)
            get=node(result,u.MaterialExpressionGetMaterialAttributes)
            # Native pin construction also works without an editor GraphNode;
            # reflected attribute arrays alone do not create commandlet pins.
            index=u.FPSModularOutfitComponent.add_robe_hem_offset_pin(get)
            if index<0:raise RuntimeError('Cannot create the original WPO output')
            wire(original_node,get,first(get),original_pin)
            old,old_pin=get,str(L.get_material_expression_output_names(get)[index])
        elif original_node:old,old_pin=original_node,original_pin
        else:old,old_pin=node(result,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,0,0)),''
        world=node(result,u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
        current=node(result,u.MaterialExpressionAdd);wire(world,current,'A');wire(old,current,'B',old_pin)
        local=node(result,u.MaterialExpressionTransformPosition,transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
        wire(current,local,first(local))
        rest=node(result,u.MaterialExpressionPreSkinnedPosition)
        inputs={'Position':local,'RestPosition':rest,'Strength':scalar(result,'RobeHemStrength',0),'Shape':vector(result,'RobeHemShape',(16,2,8))}
        for i in range(64):inputs['P'+str(i)]=vector(result,'RobeHemPoint'+str(i))
        custom=node(result,u.MaterialExpressionCustom,description=marker,code=CODE,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
        pins=[]
        for name in inputs:
            pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
        custom.set_editor_property('inputs',pins)
        for name,n in inputs.items():wire(n,custom,name,'RGB' if isinstance(n,u.MaterialExpressionVectorParameter) else '')
        # Pixel coverage uses the final displaced position. This is a material
        # mask only; no scene-depth reads, extra captures or render passes.
        visible_world=node(result,u.MaterialExpressionWorldPosition)
        visible_local=node(result,u.MaterialExpressionTransformPosition,transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
        wire(visible_world,visible_local,first(visible_local))
        rest_pixel=node(result,u.MaterialExpressionVertexInterpolator)
        wire(rest,rest_pixel,first(rest_pixel))
        mask_inputs={'Position':visible_local,'RestPosition':rest_pixel,'Strength':inputs['Strength'],'Shape':inputs['Shape']}
        for i in range(16):mask_inputs['P'+str(i)]=inputs['P'+str(i)]
        mask=node(result,u.MaterialExpressionCustom,description='Robe hem covered-region visibility',code=MASK_CODE,output_type=u.CustomMaterialOutputType.CMOT_FLOAT1)
        mask_pins=[]
        for name in mask_inputs:
            pin=u.CustomInput();pin.set_editor_property('input_name',name);mask_pins.append(pin)
        mask.set_editor_property('inputs',mask_pins)
        for name,n in mask_inputs.items():wire(n,mask,name,'RGB' if isinstance(n,u.MaterialExpressionVectorParameter) else '')
        if attrs and was_masked:
            mask_index=u.FPSModularOutfitComponent.add_robe_hem_mask_pin(get)
            if mask_index<0:raise RuntimeError('Cannot read original opacity mask')
            original_mask=get;mask_pin=str(L.get_material_expression_output_names(get)[mask_index])
        if original_mask:
            combined_mask=node(result,u.MaterialExpressionMultiply)
            wire(original_mask,combined_mask,'A',mask_pin);wire(mask,combined_mask,'B');mask=combined_mask
        offset=node(result,u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        wire(custom,offset,first(offset))
        total=node(result,u.MaterialExpressionAdd);wire(old,total,'A',old_pin);wire(offset,total,'B')
        if attrs:
            set_attrs=node(result,u.MaterialExpressionSetMaterialAttributes)
            index=u.FPSModularOutfitComponent.add_robe_hem_offset_pin(set_attrs)
            if index<0:raise RuntimeError('Cannot create the combined WPO input')
            names=L.get_material_expression_input_names(set_attrs)
            wire(original_node,set_attrs,str(names[0]),original_pin);wire(total,set_attrs,str(names[index]));output=set_attrs
            mask_index=u.FPSModularOutfitComponent.add_robe_hem_mask_pin(set_attrs)
            if mask_index<0:raise RuntimeError('Cannot create the inner-layer opacity mask')
            wire(mask,set_attrs,str(L.get_material_expression_input_names(set_attrs)[mask_index]))
        else:output=total
        if not L.connect_material_property(output,'',prop):raise RuntimeError('Cannot connect hem offset '+original)
        if not attrs and not L.connect_material_property(mask,'',u.MaterialProperty.MP_OPACITY_MASK):raise RuntimeError('Cannot connect inner-layer mask '+original)
        result.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
        L.set_base_material_usage(result,u.MaterialUsage.MATUSAGE_SKELETAL_MESH,True)
        errors=L.recompile_material(result)
        if errors:raise RuntimeError('Hem material compilation: '+str(errors))
    else:raise RuntimeError('Unsupported original surface '+original)
    E.set_metadata_tag(result,'RobeHemShaderSHA',REV);E.set_metadata_tag(result,'RobeHemOriginalMaterial',original)
    if not E.save_loaded_asset(result,False):raise RuntimeError('Cannot save hem surface '+path)
    cache[original]=result;return result
