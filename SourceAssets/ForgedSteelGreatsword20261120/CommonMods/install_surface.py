"""Build one native blade surface for the standard runes and five shared steels."""
from pathlib import Path
import json
import runpy
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
REV = 'ForgedSteelCommonSurfaceV1'
BASE = '/Game/Weapons/ForgedSteelGreatsword20261120/V1/Materials/M_ForgedSteelGreatsword_Surface_V1'
# The shared runtime recognizes this native rune material family on held and body meshes.
TARGET = '/Game/Weapons/ForgedSteelGreatsword20261120/CommonMods/Materials/M_TangDaoBladeRuneSurface_ForgedSteel_V1'
recipes = json.loads((ROOT/'SourceAssets/SharedTwoHandMaterials20261101/common-recipes.json').read_text(encoding='utf8'))

def load(path):
    obj = u.load_asset(path)
    if not obj: raise RuntimeError('Missing material dependency: ' + path)
    return obj

def connect(a, output_name, b, pin):
    if not L.connect_material_expressions(a, '' if str(output_name) == 'None' else str(output_name), b, '' if str(pin) == 'None' else str(pin)):
        raise RuntimeError('Could not connect material expression: ' + str(pin))

def add_native_runes(material):
    source=load('/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2')
    originals=list(L.get_material_expressions(source))
    copies={node.get_name():L.duplicate_material_expression(material,None,node) for node in originals}
    for node in originals:
        for input_node,name in zip(L.get_inputs_for_material_expression(source,node),L.get_material_expression_input_names(node)):
            if input_node:connect(copies[input_node.get_name()],L.get_input_node_output_name_for_material_expression(node,input_node),copies[node.get_name()],name)
    rgb=L.get_material_property_input_node(source,u.MaterialProperty.MP_EMISSIVE_COLOR)
    coverage=L.get_material_property_input_node(source,u.MaterialProperty.MP_OPACITY)
    emission=copies[rgb.get_name()];opacity=copies[coverage.get_name()]
    multiply=L.create_material_expression(material,u.MaterialExpressionMultiply)
    if isinstance(rgb,u.MaterialExpressionEyeAdaptationInverse):
        original_input=L.get_inputs_for_material_expression(source,rgb)[0]
        connect(copies[original_input.get_name()],'',multiply,'A');connect(opacity,'',multiply,'B')
        connect(multiply,'',emission,L.get_material_expression_input_names(emission)[0])
    else:
        connect(emission,'',multiply,'A');connect(opacity,'',multiply,'B');emission=multiply
    front=L.get_material_property_input_node(material,u.MaterialProperty.MP_FRONT_MATERIAL)
    if not isinstance(front,u.MaterialExpressionSubstrateShadingModels):raise RuntimeError('Unsupported PBR front node')
    connect(emission,'',front,'Emissive Color')
    if not L.connect_material_property(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR):raise RuntimeError('Emissive output missing')

def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(src,dst,pin,channel=''):
    names=[str(n) for n in L.get_material_expression_input_names(dst)]
    normalize=lambda s:s.replace(' ','').replace('_','').lower()
    actual=next((n for n in names if normalize(n)==normalize(pin)),None)
    if actual is None and pin=='Input' and len(names)==1:actual=names[0]
    if actual is None or not L.connect_material_expressions(src,channel,dst,actual):raise RuntimeError('Pin '+pin+' '+str(names))
def custom(m,label,code,width,inputs):
    n=node(m,u.MaterialExpressionCustom,desc=REV+' '+label,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    n.set_editor_property('inputs',pins)
    for name,(src,out) in inputs.items():wire(src,n,name,out)
    return n
def root(m,field):
    prop=getattr(u.MaterialProperty,'MP_'+field);src=L.get_material_property_input_node(m,prop)
    return src,str(L.get_material_property_input_node_output_name(m,prop)) if src else ''
def output(src,field):
    if not L.connect_material_property(src,'',getattr(u.MaterialProperty,'MP_'+field)):raise RuntimeError('Output '+field)
texture=u.load_asset('/Game/Weapons/AzureRunesword20260913/MeteoricIronRefinement20261101/T_MeteoricCrystalFieldV2')
if not texture:raise RuntimeError('Meteor crystal field missing')

m = load(TARGET) if E.does_asset_exist(TARGET) else E.duplicate_asset(BASE,TARGET)
if not m: raise RuntimeError('Could not create native steel blade material')
if E.get_metadata_tag(m,'ForgedSteelCommonSurface') != REV:
    add_native_runes(m)
    for n in L.get_material_expressions(m):
        if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='RuneMode':
            n.set_editor_property('default_value',-1.)
    original_emission=root(m,'EMISSIVE_COLOR')
    mode=node(m,u.MaterialExpressionScalarParameter,parameter_name='BladeFinishMode',default_value=0.)
    mask=node(m,u.MaterialExpressionConstant,r=0.)
    pos=node(m,u.MaterialExpressionVertexInterpolator);wire(node(m,u.MaterialExpressionPreSkinnedPosition),pos,'Input')
    normal=node(m,u.MaterialExpressionVertexInterpolator);wire(node(m,u.MaterialExpressionPreSkinnedNormal),normal,'Input')
    # Use each face's dominant plane: broad hammer faces must not collapse to a line.
    coords=custom(m,'surface coordinates','float3 a=abs(N);return a.x>a.y && a.x>a.z?float3(P.y,P.x,P.z):a.z>a.y?float3(P.x,P.z,P.y):P;',3,{'P':(pos,''),'N':(normal,'')})
    uv=custom(m,'crystal atlas','return frac(float2((P.x+16)/32,(P.z+64)/128));',2,{'P':(coords,'')})
    crystal=node(m,u.MaterialExpressionTextureSample,texture=texture,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    wire(uv,crystal,'UVs')
    edge=custom(m,'beveled edges','float3 a=abs(normalize(N));return 1-smoothstep(.75,.96,max(a.x,max(a.y,a.z)));',1,{'N':(normal,'')})
    for field,code in recipes.items():
        src,out=root(m,field);target=None
        if not src:raise RuntimeError('Missing PBR '+field+' '+TARGET)
        if isinstance(src,u.MaterialExpressionCustom) and 'Data.' in str(src.get_editor_property('code')):
            for name,inp in zip(L.get_material_expression_input_names(src),L.get_inputs_for_material_expression(m,src)):
                if str(name)=='Base' and inp:
                    target=src;src=inp;out=str(L.get_input_node_output_name_for_material_expression(target,src));break
        inputs={'Base':(src,out),'Mode':(mode,''),'Mask':(mask,'')}
        if field!='METALLIC':inputs['P']=(coords,'')
        if field in ['BASE_COLOR','ROUGHNESS']:inputs.update(Crystal=(crystal,'RGBA'),Edge=(edge,''))
        result=custom(m,field,code,3 if field in ['BASE_COLOR','NORMAL'] else 1,inputs)
        if target:wire(result,target,'Base')
        else:output(result,field)
    direction=custom(m,'crystal brush direction',
        'float2 d=normalize(Crystal.rg*2-1+float2(.0001,0));float3 a=abs(N);float3 v=a.x>a.y&&a.x>a.z?float3(0,d.x,d.y):a.z>a.y?float3(d.x,d.y,0):float3(d.x,0,d.y);return normalize(v-N*dot(v,N)+float3(.00001,0,.00001));',
        3,{'Crystal':(crystal,'RGBA'),'N':(normal,'')})
    tangent_space=bool(m.get_editor_property('tangent_space_normal'))
    transform=node(m,u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
        transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT if tangent_space else u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    wire(direction,transform,'Input')
    for field,code in [('ANISOTROPY','if(Mode>4.5&&Mode<5.5)return (.20+.07*Crystal.a)*(1-.7*Edge);return Base;'),
                       ('TANGENT','if(Mode>4.5&&Mode<5.5)return Brush;return Base;')]:
        src,out=root(m,field)
        if not src:src=node(m,u.MaterialExpressionConstant,r=0.) if field=='ANISOTROPY' else (node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(1,0,0,1)) if tangent_space else node(m,u.MaterialExpressionVertexTangentWS))
        inputs={'Base':(src,out),'Mode':(mode,'')}
        if field=='ANISOTROPY':inputs.update(Crystal=(crystal,'RGBA'),Edge=(edge,''))
        else:inputs['Brush']=(transform,'')
        output(custom(m,field,code,1 if field=='ANISOTROPY' else 3,inputs),field)
    slab,_=root(m,'FRONT_MATERIAL')
    if not slab:slab=node(m,u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    if not isinstance(slab,u.MaterialExpressionSubstrateShadingModels):raise RuntimeError('Unexpected Substrate output '+TARGET)
    for field,pin in [('BASE_COLOR','BaseColor'),('METALLIC','Metallic'),('SPECULAR','Specular'),('ROUGHNESS','Roughness'),
                      ('NORMAL','Normal'),('EMISSIVE_COLOR','EmissiveColor'),('ANISOTROPY','Anisotropy'),('TANGENT','Tangent')]:
        src,out=root(m,field)
        if src:wire(src,slab,pin,out)
    output(slab,'FRONT_MATERIAL')
    if root(m,'EMISSIVE_COLOR')!=original_emission:raise RuntimeError('Native rune emission changed '+TARGET)

    L.layout_material_expressions(m)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Blade material compile failed: '+str(errors))
    E.set_metadata_tag(m,'ForgedSteelCommonSurface',REV)
    if not E.save_loaded_asset(m,False):raise RuntimeError('Blade material save failed')

apply_damascus = runpy.run_path(str(ROOT/'SourceAssets/SharedTwoHandMaterials20261101/damascus_v3.py'))['apply_registered']
if apply_damascus(m):
    errors=L.recompile_material(m)
    if errors or not E.save_loaded_asset(m,False):raise RuntimeError('Damascus blade surface: '+str(errors))

temporal_path=TARGET+'_Whirlwind'
temporal=load(temporal_path) if E.does_asset_exist(temporal_path) else E.duplicate_asset(TARGET,temporal_path)
if not temporal:raise RuntimeError('Could not create temporal blade material')
if not any(isinstance(n,u.MaterialExpressionTemporalResponsivenessOutput) for n in L.get_material_expressions(temporal)):
    response=node(temporal,u.MaterialExpressionTemporalResponsivenessOutput)
    connect(node(temporal,u.MaterialExpressionConstant,r=1.),'',response,'')
    errors=L.recompile_material(temporal)
    if errors:raise RuntimeError('Temporal material compile failed: '+str(errors))
if apply_damascus(temporal):
    errors=L.recompile_material(temporal)
    if errors:raise RuntimeError('Temporal Damascus blade surface: '+str(errors))
if not E.save_loaded_asset(temporal,False):raise RuntimeError('Temporal blade material save failed')
factory=json.loads((P.parent/'Integration/exports.json').read_text(encoding='utf8'))
blade=next(row for row in factory['parts'] if row['slot']=='blade_1')
paths={'factory':factory['ue_root']+'/Meshes/'+blade['mesh']}
variants=json.loads((P/'variant_exports.json').read_text(encoding='utf8'))['options']
for row in variants:
    if row['slot']=='blade_1':
        paths[row['option']]=TARGET.split('/Materials/')[0]+'/Meshes/'+row['mesh']
slots={key:[str(slot.material_slot_name) for slot in load(path).static_materials] for key,path in paths.items()}
(P/'blade_materials.json').write_text(json.dumps({'base':m.get_path_name(),'whirlwind':temporal.get_path_name(),'slots':slots},indent=2)+'\n',encoding='utf8')
