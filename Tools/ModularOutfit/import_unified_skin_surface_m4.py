"""Save V5 skin materials on a direct V4 mesh duplicate; no geometry rebuild.

Uses existing textures and the current editor's serialized authoring bridge.
Nothing is published until both materials and the derivative mesh are saved.
"""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
BASE=PROJECT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4'
ROOT=BASE/'UnifiedSkinSurfaceV5'
OLD='/Game/Characters/ModularOutfit20260924/OriginalShapeBareM4WristV4'
DEST='/Game/Characters/ModularOutfit20260924/OriginalShapeBareM4SurfaceV5'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Finish play before saving the V5 skin materials; no assets have been changed')
ROOT.mkdir(parents=True,exist_ok=True)
code_path=PROJECT/'Tools/ModularOutfit/skin_surface_v5.hlsl'
code=code_path.read_text()
shutil.copy2(code_path,ROOT/'skin_surface.hlsl')
parameters=json.loads((BASE/'WristContourV4/micro_surface.json').read_text())
shape=json.loads((BASE/'WristContourV4/M4_bare_shape.json').read_text())
frame=shape['anatomy']['r']
saved=[]

def save(asset):
    if not E.save_loaded_asset(asset,False):
        raise RuntimeError('Cannot save '+asset.get_path_name())
    saved.append(asset.get_path_name())

def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Required V4 material input missing: '+path)
    return asset

source=load(OLD+'/SK_M4_OriginalShape_BareHands')
profile=u.load_asset(DEST+'/SSP_M4UnifiedSkin')
if not profile:profile=A.duplicate_asset('SSP_M4UnifiedSkin',DEST,load(OLD+'/SSP_RefinedM4Skin'))
settings=profile.get_editor_property('settings')
settings.set_editor_property('mean_free_path_distance',.15)
settings.set_editor_property('enable_burley',True)
profile.set_editor_property('settings',settings);save(profile)
textures={s:load(OLD+'/T_M4OriginalShape_'+s) for s in ('SkinColour','SkinNormal','SkinSurface','SkinMicro','SkinColourDetail')}
forearm_tex=load('/Game/Characters/ArmsSkinSleeveCandidate/T_Manny_ForearmRegions')
source_normal=load('/Game/Weapons/M4InfimaV3/T_Manny_02_N')
materials=[]

for forearm in (True,False):
    suffix='Forearm' if forearm else 'Hand'
    name='M_M4UnifiedSkin_'+suffix
    mat=u.load_asset(DEST+'/'+name)
    if not mat:mat=A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat)

    def node(cls,**props):
        value=L.create_material_expression(mat,cls)
        for key,data in props.items():value.set_editor_property(key,data)
        return value
    def scalar(name,value):return node(u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
    def constant(value):return node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*value,1))
    def wire(a,b,pin,output=''):
        if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Cannot connect '+pin)
    def sample(name,texture,kind):return node(u.MaterialExpressionTextureSampleParameter2D,parameter_name=name,texture=texture,sampler_type=kind)
    def interpolate(expression):
        out=node(u.MaterialExpressionVertexInterpolator);wire(expression,out,'');return out
    def world_axis(axis):
        out=node(u.MaterialExpressionTransform,
                 transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,
                 transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        wire(constant(axis),out,'');return out
    def output(expression,pin,prop):
        if not L.connect_material_property(expression,pin,prop):raise RuntimeError('Cannot connect '+str(prop))

    surface=sample('AnatomicalSurface',textures['SkinSurface'],u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    inputs={
        'UV':node(u.MaterialExpressionTextureCoordinate),
        'RestPosition':interpolate(node(u.MaterialExpressionPreSkinnedPosition)),
        'RestNormal':interpolate(node(u.MaterialExpressionPreSkinnedNormal)),
        'PositionWS':node(u.MaterialExpressionWorldPosition),
        'NormalWS':world_axis((0,0,1)), 'TangentWS':world_axis((1,0,0)), 'BitangentWS':world_axis((0,1,0)),
        'ViewWS':node(u.MaterialExpressionCameraVectorWS),
        'AnatomicalNormal':constant((0,0,1)) if forearm else sample('AnatomicalNormal',textures['SkinNormal'],u.MaterialSamplerType.SAMPLERTYPE_NORMAL),
        'BaseColour':constant((.372,.232,.182)) if forearm else (sample('AnatomicalColour',textures['SkinColour'],u.MaterialSamplerType.SAMPLERTYPE_COLOR),'RGB'),
        'Surface':node(u.MaterialExpressionConstant4Vector,constant=u.LinearColor(0,.49,0,0)) if forearm else (surface,'RGBA'),
        'ForearmMode':node(u.MaterialExpressionConstant,r=1 if forearm else 0),
        'Forearm':(sample('ForearmRegions',forearm_tex,u.MaterialSamplerType.SAMPLERTYPE_MASKS),'RGBA') if forearm else node(u.MaterialExpressionConstant4Vector,constant=u.LinearColor(1,1,0,0)),
        'SourceNormal':sample('OriginalClothNormal',source_normal,u.MaterialSamplerType.SAMPLERTYPE_NORMAL) if forearm else constant((0,0,1)),
        'SleeveTint':constant((.02,.024,.027)), 'WristTint':constant((.372,.232,.182)),
        'WristOrigin':constant(frame['wrist']), 'WristForward':constant(frame['forward']), 'WristDorsal':constant(frame['dorsal']),
        'MicroTexture':node(u.MaterialExpressionTextureObjectParameter,parameter_name='SkinMicroHeight',texture=textures['SkinMicro'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),
        'ColourDetail':node(u.MaterialExpressionTextureObjectParameter,parameter_name='SkinColourDetail',texture=textures['SkinColourDetail'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),
        'MicroTileCm':scalar('MicroTileCm',8), 'MicroTextureSize':scalar('MicroTextureSize',2048),
        'MicroHeightCm':scalar('MicroHeightCm',parameters['height_range_cm']),
        'MicroHeightZero':scalar('MicroHeightZero',parameters['height_zero']),
        'MicroNormalStrength':scalar('MicroNormalStrength',1.2),
        'ColourDetailStrength':scalar('ColourDetailStrength',.55),
        'RoughnessOffset':scalar('RoughnessOffset',0), 'SkinScatterStrength':scalar('SkinScatterStrength',.10)}
    custom=node(u.MaterialExpressionCustom,code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,
                description='V5 shared physical skin; native bind-pose triplanar coordinates')
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    custom.set_editor_property('inputs',pins)
    outputs=[]
    for name,kind in [('OutColour',u.CustomMaterialOutputType.CMOT_FLOAT3),('OutRoughness',u.CustomMaterialOutputType.CMOT_FLOAT1),('OutScatter',u.CustomMaterialOutputType.CMOT_FLOAT1)]:
        item=u.CustomOutput();item.set_editor_property('output_name',name);item.set_editor_property('output_type',kind);outputs.append(item)
    custom.set_editor_property('additional_outputs',outputs)
    for name,value in inputs.items():
        expression,pin=value if isinstance(value,tuple) else (value,'')
        wire(expression,custom,name,pin)
    for pin,prop in [('',u.MaterialProperty.MP_NORMAL),('OutColour',u.MaterialProperty.MP_BASE_COLOR),('OutRoughness',u.MaterialProperty.MP_ROUGHNESS),('OutScatter',u.MaterialProperty.MP_OPACITY)]:
        output(custom,pin,prop)
    output(scalar('SkinSpecular',.35),'',u.MaterialProperty.MP_SPECULAR)
    output(node(u.MaterialExpressionConstant,r=0),'',u.MaterialProperty.MP_METALLIC)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_SUBSURFACE_PROFILE)
    mat.set_editor_property('subsurface_profile',profile)
    L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    L.layout_material_expressions(mat)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Skin material compilation failed: '+str(errors))
    save(mat)
    instance_name='MI_M4UnifiedSkin_'+suffix
    instance=u.load_asset(DEST+'/'+instance_name)
    if not instance:instance=A.create_asset(instance_name,DEST,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(instance,mat);L.update_material_instance(instance);save(instance)
    materials.append(instance)

# Direct asset duplication preserves accepted geometry, skeleton, skin weights,
# normals, UVs and built LODs. Only slots 1 and 2 receive the two new instances.
mesh=u.load_asset(DEST+'/SK_M4_OriginalShape_BareHands')
if not mesh:mesh=A.duplicate_asset('SK_M4_OriginalShape_BareHands',DEST,source)
slots=[slot.copy() for slot in source.materials]
for index,material in zip((1,2),materials):
    slots[index].set_editor_property('material_interface',material)
mesh.set_editor_property('materials',slots)
E.set_metadata_tag(mesh,'SkinSurfaceAuthoring','V5 shared 8 cm reference-pose skin; geometry duplicated verbatim from accepted V4')
save(mesh)
config_path=PROJECT/'Content/ColdSteelData/modular_outfits.json'
config=json.loads(config_path.read_text(encoding='utf-8-sig'))
entry=config['profiles'][shape['source']]
previous=entry['bare_arms_candidate'];entry['bare_arms_candidate']=mesh.get_path_name()
config_path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt={'mesh':mesh.get_path_name(),'previous_candidate':previous,'geometry_source':source.get_path_name(),
         'saved_assets':saved,'texture_dependencies':{s:t.get_path_name() for s,t in textures.items()},
         'shader_sha256':hashlib.sha256(code.encode()).hexdigest(), 'physical_tile_cm':8,
         'shared_scatter_strength':.10,'shared_profile_mfp_cm':.15,
         'geometry_rebuilt':False,'runtime_tested':False,'visual_acceptance':'Pending user test',
         'scope':'M4 first-person with modular shirt and gloves unequipped',
         'provenance':'../RefinedSkinV3/External/SkinHuman002/provenance.json',
         'performance':'Three projections, one bounded height offset, nine detail samples; no POM loop, WPO, new texture allocation or runtime CPU logic'}
(ROOT/'saved.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('M4_UNIFIED_SKIN_V5_SAVED',mesh.get_path_name())
