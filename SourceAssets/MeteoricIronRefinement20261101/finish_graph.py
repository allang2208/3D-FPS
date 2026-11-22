"""Native rune-sword material graph edits shared by both installation entry points."""
import unreal as u

L = u.MaterialEditingLibrary
REV = 'MeteoricIron20261101V2'


def node(m,cls,**props):
    result=L.create_material_expression(m,cls)
    for key,value in props.items():result.set_editor_property(key,value)
    return result

def wire(src,dst,pin,channel=''):
    names=[str(n) for n in L.get_material_expression_input_names(dst)]
    norm=lambda s:s.replace(' ','').replace('_','').lower()
    actual=next((n for n in names if norm(n)==norm(pin)),None)
    if actual is None and pin=='Input' and len(names)==1:actual=names[0]
    if actual is None or not L.connect_material_expressions(src,channel,dst,actual):raise RuntimeError('Material pin '+pin+' '+str(names))

def out(src,name):
    if not L.connect_material_property(src,'',getattr(u.MaterialProperty,'MP_'+name)):raise RuntimeError('Material output '+name)

def custom(m,label,code,width,inputs):
    result=node(m,u.MaterialExpressionCustom,desc=REV+' '+label,code=code,
                output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    result.set_editor_property('inputs',pins)
    for name,(source,channel) in inputs.items():wire(source,result,name,channel)
    return result

def add_input(expression,name,src,channel=''):
    pins=list(expression.get_editor_property('inputs'))
    pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    expression.set_editor_property('inputs',pins);wire(src,expression,name,channel)

def input_source(m,expression,name):
    for pin,source in zip(L.get_material_expression_input_names(expression),L.get_inputs_for_material_expression(m,expression)):
        if str(pin)==name and source:return source,str(L.get_input_node_output_name_for_material_expression(expression,source))
    raise RuntimeError('Existing input missing '+name)

def remove_old_branch(code):
    marker='// MeteoricIron20261031V1'
    start=code.find(marker)
    if start<0:raise RuntimeError('Expected current meteor mode 5 branch')
    opening=code.index('{',start);depth=1;end=opening+1
    while depth:
        if code[end]=='{':depth+=1
        elif code[end]=='}':depth-=1
        end+=1
    return code[:start]+code[end:]

RECIPES={
 'MP_BASE_COLOR':'''float w=1-saturate(Mask*3.0);
float tone=.30+(Crystal.b-.5)*.026;
float3 metal=float3(.985,1,1.018)*tone;
metal=lerp(metal,float3(.37,.375,.38),Edge*.50);
return lerp(Base,metal,w);''',
 'MP_ROUGHNESS':'''float w=1-saturate(Mask*3.0);
float2 brush=normalize(Crystal.rg*2-1+float2(.0001,0));
float phase=dot(P.xz,float2(-brush.y,brush.x))*180;
float pw=fwidth(phase);
float polish=sin(phase)*exp2(-.45*pw*pw);
float satin=.31+(Crystal.a-.5)*.06+polish*.003;
return lerp(Base,lerp(satin,.215,Edge),w);''',
 'MP_NORMAL':'return Base;',
 'MP_METALLIC':'return lerp(Base,.96,1-saturate(Mask*3.0));'}


def apply(mat, texture):
    path = mat.get_path_name()
    finishes=[n for n in L.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionCustom)
              and str(n.get_editor_property('desc')).startswith('BladeFinish20261031V1 ')]
    if len(finishes)!=4:raise RuntimeError('Current blade finish graph missing')
    color=next(n for n in finishes if 'MP_BASE_COLOR:' in str(n.get_editor_property('desc')))
    position=input_source(mat,color,'P');mode=input_source(mat,color,'Mode');mask=input_source(mat,color,'Mask')
    uv=custom(mat,'physical coordinate atlas','return float2((P.x+8)/16,(P.z+8)/128);',2,{'P':position})
    sample=node(mat,u.MaterialExpressionTextureSample,texture=texture,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR,desc=REV+' CrystalField')
    wire(uv,sample,'UVs')
    local_normal=node(mat,u.MaterialExpressionPreSkinnedNormal)
    normal_interp=node(mat,u.MaterialExpressionVertexInterpolator);wire(local_normal,normal_interp,'Input')
    edge=custom(mat,'polished narrow geometric bevel','return smoothstep(.45,.82,abs(normalize(N).x));',1,{'N':(normal_interp,'')})
    for field,recipe in RECIPES.items():
        finish=next(n for n in finishes if field+':' in str(n.get_editor_property('desc')))
        original=str(finish.get_editor_property('code'))
        if field!='MP_METALLIC':original=remove_old_branch(original)
        if field in ['MP_BASE_COLOR','MP_ROUGHNESS']:
            add_input(finish,'Crystal',sample,'RGBA');add_input(finish,'Edge',edge)
        finish.set_editor_property('code','// '+REV+'\nif(Mode>4.5 && Mode<5.5){\n'+recipe+'\n}\n'+original)
    # Grain direction is transformed through the actual mesh tangent basis.
    # Structural normal maps remain untouched; no atlas vector is treated as a UV0 normal.
    direction=custom(mat,'crystal brush direction',
        'float2 d=normalize(Crystal.rg*2-1+float2(.0001,0));float3 v=float3(d.x,0,d.y);return normalize(v-N*dot(v,N)+float3(0,0,.00001));',
        3,{'Crystal':(sample,'RGBA'),'N':(normal_interp,'')})
    tangent_space=bool(mat.get_editor_property('tangent_space_normal'))
    transform=node(mat,u.MaterialExpressionTransform,
        transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
        transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT if tangent_space else u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    wire(direction,transform,'Input')
    slab=L.get_material_property_input_node(mat,u.MaterialProperty.MP_FRONT_MATERIAL)
    if not slab:raise RuntimeError('Current Substrate output missing')
    for field,code,new_input in [
        ('ANISOTROPY','if(Mode>4.5 && Mode<5.5)return lerp(Base,(.20+.07*Crystal.a)*(1-.7*Edge),1-saturate(Mask*3.0));return Base;',None),
        ('TANGENT','if(Mode>4.5 && Mode<5.5)return normalize(lerp(Base,Brush,1-saturate(Mask*3.0)));return Base;',transform)]:
        prop=getattr(u.MaterialProperty,'MP_'+field)
        original=L.get_material_property_input_node(mat,prop)
        output=str(L.get_material_property_input_node_output_name(mat,prop)) if original else ''
        if not original:
            original=node(mat,u.MaterialExpressionConstant,r=0.) if field=='ANISOTROPY' else (
                node(mat,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(1,0,0,1)) if tangent_space else node(mat,u.MaterialExpressionVertexTangentWS))
        inputs={'Base':(original,output),'Mode':mode,'Mask':mask}
        if field=='ANISOTROPY':inputs.update(Crystal=(sample,'RGBA'),Edge=(edge,''))
        else:inputs['Brush']=(new_input,'')
        result=custom(mat,field,code,1 if field=='ANISOTROPY' else 3,inputs)
        out(result,field);wire(result,slab,'Anisotropy' if field=='ANISOTROPY' else 'Tangent')
