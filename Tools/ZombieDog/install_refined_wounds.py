"""Import the V5 wound layers and bind the existing zombie dog; no gameplay run."""
import json
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/ZombieDogRefinedWoundsV5'
DEST='/Game/Monsters/ZombieDog/RefinedWoundsV5'
PREVIOUS='/Game/Monsters/ZombieDog/RandomWoundsV4'
LIB=u.EditorAssetLibrary; MEL=u.MaterialEditingLibrary; TOOLS=u.AssetToolsHelpers.get_asset_tools()

def save(asset):
    if not LIB.save_loaded_asset(asset,False): raise RuntimeError('Could not save '+asset.get_path_name())

def duplicate(source,name):
    path=DEST+'/'+name
    return u.load_asset(path) if LIB.does_asset_exist(path) else LIB.duplicate_asset(source,path)

textures={name:u.load_asset(PREVIOUS+'/Textures/T_ZombieDog_Random_'+name)
          for name in ['CoatBase','SkinBase','CoatNormal','SkinNormal','SurfaceData']}
for semantic,name,extension in [('RestPosition','T_ZombieDog_RefinedRestPosition','.exr'),
                                ('WoundMasks','T_ZombieDog_WoundMasks','.png'),
                                ('WoundDetail','T_ZombieDog_WoundDetail','.exr')]:
    path=DEST+'/Textures/'+name
    tex=u.load_asset(path) if LIB.does_asset_exist(path) else None
    if tex is None:
        task=u.AssetImportTask(); task.filename=str(ROOT/'Textures'/(name+extension))
        task.destination_path=DEST+'/Textures'; task.destination_name=name; task.automated=True; task.save=True
        TOOLS.import_asset_tasks([task]); tex=u.load_asset(path)
        if tex is None: raise RuntimeError('Import failed: '+name)
    tex.set_editor_property('srgb',False)
    # Keep small scab masks free of block-compression artefacts. The relief map
    # uses half floats so its sub-millimetre slope is not quantized to 8-bit steps.
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_HDR if extension=='.exr'
                            else u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP)
    tex.set_editor_property('address_x',u.TextureAddress.TA_CLAMP)
    tex.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
    if semantic=='RestPosition':
        tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        tex.set_editor_property('never_stream',True)
    save(tex); textures[semantic]=tex

path=DEST+'/Materials/M_ZombieDog_RefinedWounds'
mat=u.load_asset(path) if LIB.does_asset_exist(path) else TOOLS.create_asset(
    'M_ZombieDog_RefinedWounds',DEST+'/Materials',u.Material,u.MaterialFactoryNew())
if LIB.get_metadata_tag(mat,'ZombieDog.RefinedWounds')!='5.1':
    MEL.delete_all_material_expressions(mat)
    mat.set_editor_property('used_with_skeletal_mesh',True)
    mat.set_editor_property('two_sided',True)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
    mat.set_editor_property('opacity_mask_clip_value',.28)

    def node(cls,**props):
        result=MEL.create_material_expression(mat,cls)
        for key,value in props.items(): result.set_editor_property(key,value)
        return result

    def link(src,output,dst,pin):
        if not MEL.connect_material_expressions(src,output,dst,pin): raise RuntimeError('Cannot connect '+pin)

    def custom(code,inputs,kind=u.CustomMaterialOutputType.CMOT_FLOAT3,extras=()):
        result=node(u.MaterialExpressionCustom,code=code,output_type=kind)
        pins=[]
        for name in inputs:
            pin=u.CustomInput(); pin.set_editor_property('input_name',name); pins.append(pin)
        result.set_editor_property('inputs',pins)
        outputs=[]
        for name in extras:
            output=u.CustomOutput(); output.set_editor_property('output_name',name)
            output.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1); outputs.append(output)
        result.set_editor_property('additional_outputs',outputs)
        for name,(src,output) in inputs.items(): link(src,output,result,name)
        return result

    def scalar(name,value):
        return node(u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)

    def vector4(name,default):
        parameter=node(u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*default))
        result=node(u.MaterialExpressionAppendVector)
        link(parameter,'RGB',result,'A'); link(parameter,'A',result,'B'); return result

    samples={}
    for semantic in ['CoatBase','SkinBase','CoatNormal','SkinNormal','SurfaceData','RestPosition']:
        sampler=(u.MaterialSamplerType.SAMPLERTYPE_NORMAL if semantic.endswith('Normal') else
                 u.MaterialSamplerType.SAMPLERTYPE_COLOR if semantic.endswith('Base') else
                 u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR if semantic=='RestPosition' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        samples[semantic]=node(u.MaterialExpressionTextureSampleParameter2D,parameter_name=semantic,
                               texture=textures[semantic],sampler_type=sampler)
    masks=node(u.MaterialExpressionTextureObjectParameter,parameter_name='WoundMasks',texture=textures['WoundMasks'],
               sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    detail=node(u.MaterialExpressionTextureObjectParameter,parameter_name='WoundDetail',texture=textures['WoundDetail'],
                sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    is_fur=scalar('IsFur',0.); fixed=scalar('FixedWound',0.)
    inputs=dict(Rest=(samples['RestPosition'],'RGB'),Seed=(scalar('WoundSeed',0.),''),FixedWound=(fixed,''),
                Masks=(masks,''),Detail=(detail,''))
    for i in range(8):
        for short,name,value in [('C','WoundCenter',(0,0,0,0)),('U','WoundU',(1,0,0,1)),
                                 ('V','WoundV',(0,1,0,1)),('N','WoundN',(0,0,1,1)),('S','WoundStyle',(0,0,.12,0))]:
            inputs[short+str(i)]=(vector4(name+str(i),value),'')
    field=custom((PROJECT/'Tools/ZombieDog/refined_wound_field.hlsl').read_text(encoding='utf-8'),inputs,
                 u.CustomMaterialOutputType.CMOT_FLOAT4,('Relief','Healing','Fibres','FurRemoval'))
    color=custom('''
float3 bloodCoat=lerp(Coat,Coat*float3(.57,.40,.35)+float3(.007,.0015,.001),L.w*.60);
float3 bruisedSkin=Skin*lerp(float3(1,1,1),float3(.86,.77,.73),L.w*.35);
float3 base=lerp(bloodCoat,bruisedSkin,L.x);
float3 scab=lerp(float3(.034,.012,.008),float3(.071,.028,.017),Fibres);
float tone=saturate(dot(Skin,float3(.2126,.7152,.0722))*5.5);
float3 tissue=lerp(float3(.070,.013,.011),float3(.14,.034,.025),tone*.55+Fibres*.45);
tissue=lerp(tissue,Skin*float3(1.04,.89,.84),Healing*.84);
base=lerp(base,tissue,L.y*.92);
base=lerp(base,scab,L.z*(1-Healing*.55));
// Remaining fur receives stain, not a flat tissue-colour coating.
return lerp(base,bloodCoat,IsFur);
''',dict(L=(field,''),Healing=(field,'Healing'),Fibres=(field,'Fibres'),IsFur=(is_fur,''),
         Coat=(samples['CoatBase'],'RGB'),Skin=(samples['SkinBase'],'RGB')))
    rough=custom('''
float wet=smoothstep(.48,.9,L.y)*(1-Healing)*(.55+.45*Fibres);
float skin=lerp(Data.g,.72,L.z);
float r=lerp(.82,skin,L.x);
r=lerp(r,.38,wet);
return lerp(r,lerp(.82,.65,L.w*.55),IsFur);
''',dict(L=(field,''),Data=(samples['SurfaceData'],'RGB'),Healing=(field,'Healing'),
         Fibres=(field,'Fibres'),IsFur=(is_fur,'')),u.CustomMaterialOutputType.CMOT_FLOAT1)
    alpha=custom('return lerp(1.0,Data.r*(1.0-Removal),IsFur);',
                 dict(Data=(samples['SurfaceData'],'RGB'),Removal=(field,'FurRemoval'),IsFur=(is_fur,'')),
                 u.CustomMaterialOutputType.CMOT_FLOAT1)
    normal=custom('return normalize(lerp(Coat,Skin,L.x*(1-IsFur)));',
                  dict(Coat=(samples['CoatNormal'],'RGB'),Skin=(samples['SkinNormal'],'RGB'),L=(field,''),IsFur=(is_fur,'')))
    world_normal=node(u.MaterialExpressionTransform,
        transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,
        transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    link(normal,'',world_normal,str(MEL.get_material_expression_input_names(world_normal)[0]))
    position=node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_CAMERA_RELATIVE_NO_OFFSETS)
    bumped=custom('''
float3 n=normalize(Normal);
float3 dx=ddx(Position),dy=ddy(Position);
float3 r1=cross(dy,n),r2=cross(n,dx);
float det=dot(dx,r1);
float inverse=sign(det)/max(abs(det),1e-6);
float3 gradient=(ddx(Height)*r1+ddy(Height)*r2)*inverse;
return normalize(n-gradient*(1-IsFur));
''',dict(Normal=(world_normal,''),Position=(position,''),Height=(field,'Relief'),IsFur=(is_fur,'')))
    tangent_normal=node(u.MaterialExpressionTransform,
        transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,
        transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
    link(bumped,'',tangent_normal,str(MEL.get_material_expression_input_names(tangent_normal)[0]))
    for src,output,prop in [(color,'',u.MaterialProperty.MP_BASE_COLOR),(rough,'',u.MaterialProperty.MP_ROUGHNESS),
        (alpha,'',u.MaterialProperty.MP_OPACITY_MASK),(tangent_normal,'',u.MaterialProperty.MP_NORMAL),
        (samples['SurfaceData'],'B',u.MaterialProperty.MP_AMBIENT_OCCLUSION),
        (scalar('Specular',.30),'',u.MaterialProperty.MP_SPECULAR)]:
        if not MEL.connect_material_property(src,output,prop): raise RuntimeError('Cannot connect '+str(prop))
    MEL.layout_material_expressions(mat)
    errors=MEL.recompile_material(mat)
    if errors: raise RuntimeError('Material compilation failed: '+'\n'.join(errors))
    LIB.set_metadata_tag(mat,'ZombieDog.RefinedWounds','5.1'); save(mat)

materials={}
for role,fur,ear in [('Body',0.,0.),('Fur',1.,0.),('EarScar',0.,1.)]:
    name='MI_ZombieDog_Refined'+role; path=DEST+'/Materials/'+name
    instance=u.load_asset(path) if LIB.does_asset_exist(path) else TOOLS.create_asset(
        name,DEST+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(instance,mat)
    MEL.set_material_instance_scalar_parameter_value(instance,'IsFur',fur)
    MEL.set_material_instance_scalar_parameter_value(instance,'FixedWound',ear)
    MEL.update_material_instance(instance); save(instance); materials[role]=instance

mesh=duplicate(PREVIOUS+'/SK_ZombieDog_RandomWounds','SK_ZombieDog_RefinedWounds')
slots=mesh.get_editor_property('materials')
for i,slot in enumerate(slots):
    role='Fur' if 'Fur' in str(slot.material_slot_name) else 'EarScar' if 'EarScar' in str(slot.material_slot_name) else 'Body'
    slot.material_interface=materials[role]; slots[i]=slot
mesh.set_editor_property('materials',slots); save(mesh)
bp=u.load_asset('/Game/Monsters/ZombieDog/V1/BP_ZombieDog')
u.BlueprintEditorLibrary.compile_blueprint(bp)
defaults=u.get_default_object(bp.generated_class())
previous=defaults.get_editor_property('animation_set')
dataset=duplicate(previous.get_path_name(),'DA_ZombieDog_RefinedWounds')
dataset.set_editor_property('reference_mesh',mesh); save(dataset)
defaults.set_editor_property('animation_set',dataset)
defaults.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
appearance=defaults.get_editor_property('wound_appearance')
appearance.set_editor_property('enabled',True); appearance.set_editor_property('random_seed',0)
appearance.set_editor_property('min_wounds',6); appearance.set_editor_property('max_wounds',8)
appearance.set_editor_property('surface_set',u.load_asset(PREVIOUS+'/DA_ZombieDog_WoundSurfaces'))
LIB.set_metadata_tag(bp,'ZombieDog.Appearance','RefinedWoundsV5'); save(bp)
(ROOT/'ue_delivery.json').write_text(json.dumps(dict(blueprint=bp.get_path_name(),mesh=mesh.get_path_name(),
    dataset=dataset.get_path_name(),previous_dataset=previous.get_path_name(),
    materials={k:v.get_path_name() for k,v in materials.items()},target_wounds=[6,8],
    distribution='enlarged torso injury, broader secondary wounds, fewer hairline scars',
    f6_entry='ZombieDog / 僵尸犬',runtime_tested=False,preview_rendered=False),ensure_ascii=False,indent=2),encoding='utf-8')
u.log('ZOMBIE_DOG_REFINED_WOUNDS_V5_INSTALLED')
