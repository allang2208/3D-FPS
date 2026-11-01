"""Add independent blade finishes to the original and native-rune PBR masters.

Defaults are identity. Finish parameters are set only on the blade component.
Existing wetness runs after the dry finish; emission and native ink are retained.
"""
from pathlib import Path
import json,shutil
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
REVISION='BladeFinish20261031V1'
MASTERS=['/Game/Weapons/AzureRunesword20260913/M_AzureRunesword',
 '/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/M_AzureRunesword_NativeGold']
PATTERN='''float phase=P.x*18.0 + sin(P.z*.31)*3.4 + sin(P.z*.87+P.x*.7)*.65;
float phaseWidth=fwidth(phase);
float bandFilter=exp2(-.35*phaseWidth*phaseWidth);
float bands=(sin(phase)*.7+sin(phase*2.7+.35)*.3)*bandFilter;
float grainPhase=P.x*370.0+sin(P.z*3.1)*.65;
float grainWidth=fwidth(grainPhase);
float grain=sin(grainPhase)*exp2(-.35*grainWidth*grainWidth);
float w=(Mode>.5 ? 1.0 : 0.0)*(1-saturate(Mask*3.0));
'''
COLOR=PATTERN+'''if(Mode<.5)return Base;
float shade=clamp(dot(Base,float3(.2126,.7152,.0722))/.32,.72,1.12);
float3 finish=Mode<1.5 ? float3(.27,.29,.31)*(1+bands*.105+grain*.009) :
 Mode<2.5 ? float3(.025,.030,.038)*(1+grain*.035) : float3(.58,.62,.67)*(1+grain*.012);
return lerp(Base,finish*shade,w);'''
ROUGH=PATTERN+'''if(Mode<.5)return Base;
float rough=Mode<1.5 ? .29+bands*.018 : Mode<2.5 ? .34+grain*.009 : .20+grain*.006;
return lerp(Base,clamp(rough+(Base-.35)*.12,.12,.55),w);'''
NORMAL=PATTERN+'''if(Mode<.5)return Base;
float detail=Mode<1.5 ? cos(phase)*.028*bandFilter+grain*.006 : Mode<2.5 ? grain*.012 : grain*.005;
return normalize(lerp(Base,normalize(float3(Base.xy+float2(detail,0),Base.z)),w));'''
METAL='''float w=(Mode>.5 ? 1.0 : 0.0)*(1-saturate(Mask*3.0)); return lerp(Base,.96,w);'''

def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for key,value in props.items():n.set_editor_property(key,value)
    return n
def link(source,output,target,pin):
    if not L.connect_material_expressions(source,output,target,pin):raise RuntimeError('Material pin connection failed: '+pin)
def custom(m,label,code,kind,inputs):
    n=node(m,u.MaterialExpressionCustom,desc=REVISION+' '+label,code=code,output_type=kind)
    pins=[]
    for name,source,output in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
    n.set_editor_property('inputs',pins)
    for name,source,output in inputs:link(source,output,n,name)
    return n

saved=[]
for path in MASTERS:
    mat=u.load_asset(path)
    if not mat:raise RuntimeError('Missing original master: '+path)
    if E.get_metadata_tag(mat,'BladeFinishRevision')==REVISION:
        saved.append({'path':mat.get_path_name(),'already_current':True});continue
    asset=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    backup=P/'BeforeAssets'/asset.relative_to(ROOT/'Content');backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(asset,backup)
    mode=node(mat,u.MaterialExpressionScalarParameter,parameter_name='BladeFinishMode',default_value=0.)
    local_position=node(mat,u.MaterialExpressionPreSkinnedPosition)
    position=node(mat,u.MaterialExpressionVertexInterpolator)
    link(local_position,'',position,'VS')
    masktex=u.load_asset('/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/T_RuneSword_NativeMask')
    sampler=u.MaterialSamplerType.SAMPLERTYPE_MASKS if masktex.get_editor_property('compression_settings')==u.TextureCompressionSettings.TC_MASKS else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
    mask=node(mat,u.MaterialExpressionTextureSample,texture=masktex,sampler_type=sampler)
    modifications=[]
    for prop,code,kind in [(u.MaterialProperty.MP_BASE_COLOR,COLOR,u.CustomMaterialOutputType.CMOT_FLOAT3),
                           (u.MaterialProperty.MP_ROUGHNESS,ROUGH,u.CustomMaterialOutputType.CMOT_FLOAT1),
                           (u.MaterialProperty.MP_NORMAL,NORMAL,u.CustomMaterialOutputType.CMOT_FLOAT3),
                           (u.MaterialProperty.MP_METALLIC,METAL,u.CustomMaterialOutputType.CMOT_FLOAT1)]:
        root=L.get_material_property_input_node(mat,prop)
        output=L.get_material_property_input_node_output_name(mat,prop)
        if not root:raise RuntimeError('Missing original PBR input '+str(prop))
        target=None;source=root
        # These masters already wrap dry inputs in the authored wetness custom.
        if isinstance(root,u.MaterialExpressionCustom) and 'Data.' in root.get_editor_property('code'):
            for name,inp in zip(L.get_material_expression_input_names(root),L.get_inputs_for_material_expression(mat,root)):
                if str(name)=='Base' and inp:
                    target=root;source=inp;output=L.get_input_node_output_name_for_material_expression(root,inp);break
        inputs=[('Base',source,output),('Mode',mode,''),('Mask',mask,'R')]
        if prop!=u.MaterialProperty.MP_METALLIC:inputs.append(('P',position,''))
        result=custom(mat,str(prop),code,kind,inputs)
        if target:link(result,'',target,'Base')
        elif not L.connect_material_property(result,'',prop):raise RuntimeError('Root PBR connection failed')
        modifications.append(str(prop))
    # Explicit Substrate output mirrors the complete current PBR graph. Keeping
    # emission separate prevents silver/gold/native rune glow from being recolored.
    slab=L.get_material_property_input_node(mat,u.MaterialProperty.MP_FRONT_MATERIAL)
    if not slab:
        slab=node(mat,u.MaterialExpressionSubstrateShadingModels,shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    names={str(n).replace(' ','').lower():str(n) for n in L.get_material_expression_input_names(slab)}
    for field,pin in [('MP_BASE_COLOR','BaseColor'),('MP_METALLIC','Metallic'),('MP_SPECULAR','Specular'),
                      ('MP_ROUGHNESS','Roughness'),('MP_NORMAL','Normal'),('MP_EMISSIVE_COLOR','EmissiveColor')]:
        prop=getattr(u.MaterialProperty,field);src=L.get_material_property_input_node(mat,prop)
        if src:link(src,L.get_material_property_input_node_output_name(mat,prop),slab,names[pin.lower()])
    if not L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Front material connection failed')
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Finish shader compilation failed: '+str(errors))
    E.set_metadata_tag(mat,'BladeFinishRevision',REVISION)
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Material not saved: '+path)
    saved.append({'path':mat.get_path_name(),'saved':True,'default_mode':0,'modified_inputs':modifications})
(P/'material-receipt.json').write_text(json.dumps({'materials':saved,'revision':REVISION,'gameplay_tested':False},indent=2)+'\n',encoding='utf8')
print('BLADE_FINISH_MATERIALS_SAVED',json.dumps(saved))
