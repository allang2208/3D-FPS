"""Share the five established finishes with actual blade/head surfaces; retain rune graphs."""
from pathlib import Path
import json, shutil, re
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;REV='SharedTwoHandFinish20261101V1'
inventory=json.loads((P/'surface-inventory.json').read_text(encoding='utf8'))
# Separate inlays, rune bands, energy cores and optical crystal remain authored materials.
exclude={'M_MeteorBronze','M_MeteorRuneBand','M_MeteorLavaCore','M_Chixiao_Brass_V1','M_Zhufeng_Brass_V1',
 'M_StarOath_FineInlay_PBRV3','M_StarOath_Optical_Crystal','M_StarOath_Rune_Energy',
 'M_FinalToll_Rune_Energy','M_FinalToll_FineInlay_PBRV3','M_AzureRunesword'}
paths=[p for p in inventory['materials'] if p.rsplit('.',1)[-1] not in exclude]
paths.extend(['/Game/Weapons/RuneboundWarhammer20261022/SwiftManaRuneV1/M_RuneboundSwiftRuneSurface.M_RuneboundSwiftRuneSurface',
 '/Game/Weapons/RuneboundWarhammer20261022/DestructionRedImpactV2/M_RuneboundDestructionRuneSurface.M_RuneboundDestructionRuneSurface'])
if u.EditorLevelLibrary.get_pie_worlds(False):raise RuntimeError('PIE running; preserve the current session')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_path_name() in [p.split('.')[0] for p in paths]:raise RuntimeError('Unsaved target '+package.get_path_name())
recipes={}
source=u.load_asset('/Game/Weapons/AzureRunesword20260913/M_AzureRunesword')
for n in L.get_material_expressions(source):
    desc=str(n.get_editor_property('desc'))
    if not isinstance(n,u.MaterialExpressionCustom) or not desc.startswith('BladeFinish20261031V1 '):continue
    field=re.search(r'MP_(\w+):',desc).group(1);code=str(n.get_editor_property('code'))
    # Copy the saved common shader recipes, excluding the two private branches.
    start=code.index('// TimeSandMaterial20261101V1');brace=code.index('{',start);end=brace+1;depth=1
    while depth:
        depth+=(code[end]=='{')-(code[end]=='}');end+=1
    code=code[:start]+code[end:]
    start=code.index('// RuneSwordFrost20261101V1');end=code.index(';',start)+1
    code=code[:start]+code[end:]
    recipes[field]=code
if set(recipes)!={'BASE_COLOR','ROUGHNESS','NORMAL','METALLIC'}:raise RuntimeError('Common recipes incomplete')
(P/'common-recipes.json').write_text(json.dumps(recipes,indent=2)+'\n',encoding='utf8')

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
saved=[]
for path in paths:
    m=u.load_asset(path)
    if E.get_metadata_tag(m,'SharedTwoHandFinishRevision')==REV:
        saved.append({'asset':path,'already_current':True});continue
    if any(isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='BladeFinishMode' for n in L.get_material_expressions(m)):
        raise RuntimeError('Unexpected existing finish on '+path)
    disk=ROOT/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
    backup=P/'BeforeAssets'/disk.relative_to(ROOT/'Content');backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(disk,backup)
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
        if not src:raise RuntimeError('Missing PBR '+field+' '+path)
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
    if not isinstance(slab,u.MaterialExpressionSubstrateShadingModels):raise RuntimeError('Unexpected Substrate output '+path)
    for field,pin in [('BASE_COLOR','BaseColor'),('METALLIC','Metallic'),('SPECULAR','Specular'),('ROUGHNESS','Roughness'),
                      ('NORMAL','Normal'),('EMISSIVE_COLOR','EmissiveColor'),('ANISOTROPY','Anisotropy'),('TANGENT','Tangent')]:
        src,out=root(m,field)
        if src:wire(src,slab,pin,out)
    output(slab,'FRONT_MATERIAL')
    if root(m,'EMISSIVE_COLOR')!=original_emission:raise RuntimeError('Native rune emission changed '+path)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('Shader compilation '+path+' '+str(errors))
    E.set_metadata_tag(m,'SharedTwoHandFinishRevision',REV)
    if not E.save_loaded_asset(m,False):raise RuntimeError('Save '+path)
    saved.append({'asset':path,'saved':True,'emission_preserved':True,'compile_errors':list(errors)})
    print('SHARED_FINISH_SAVED',len(saved),len(paths),path)
(P/'material-receipt.json').write_text(json.dumps({'revision':REV,'materials':saved,'protected_materials':sorted(exclude)},indent=2)+'\n',encoding='utf8')
print('SHARED_TWO_HAND_FINISH_COMPLETE',len(saved))
