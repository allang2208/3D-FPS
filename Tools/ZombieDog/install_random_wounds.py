"""Create random-wound material assets and bind the existing F6 zombie dog.

Run after author_random_wounds.py and the necessary editor module build.
Uses commandlet rendering only for material shader compilation, not previews.
"""
import json
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/ZombieDogRandomWoundsV4'
DEST = '/Game/Monsters/ZombieDog/RandomWoundsV4'
LIB = u.EditorAssetLibrary; MEL = u.MaterialEditingLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()

def save(asset):
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save '+asset.get_path_name())

def duplicate(source, name):
    path = DEST+'/'+name
    return u.load_asset(path) if LIB.does_asset_exist(path) else LIB.duplicate_asset(source, path)

textures = {}
for semantic in ['CoatBase', 'SkinBase', 'SurfaceData', 'CoatNormal', 'SkinNormal', 'RestPosition']:
    name = 'T_ZombieDog_Random_'+semantic; path = DEST+'/Textures/'+name
    tex = u.load_asset(path) if LIB.does_asset_exist(path) else None
    if tex is None:
        task = u.AssetImportTask()
        task.filename = str(ROOT/'Textures'/(name+('.exr' if semantic == 'RestPosition' else '.png')))
        task.destination_name = name; task.destination_path = DEST+'/Textures'
        task.automated = True; task.save = True
        TOOLS.import_asset_tasks([task]); tex = u.load_asset(path)
        if tex is None:
            raise RuntimeError('Import failed for '+semantic)
    tex.set_editor_property('srgb', semantic.endswith('Base'))
    compression = (u.TextureCompressionSettings.TC_NORMALMAP if semantic.endswith('Normal') else
                   u.TextureCompressionSettings.TC_HDR if semantic == 'RestPosition' else
                   u.TextureCompressionSettings.TC_DEFAULT if semantic.endswith('Base') else
                   u.TextureCompressionSettings.TC_MASKS)
    tex.set_editor_property('compression_settings', compression)
    if semantic == 'RestPosition':
        # UV islands may be physically far apart. Never average their coordinates
        # through lower mip levels; this shared 2K half-float atlas stays resident.
        tex.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        tex.set_editor_property('never_stream', True)
        tex.set_editor_property('address_x', u.TextureAddress.TA_CLAMP)
        tex.set_editor_property('address_y', u.TextureAddress.TA_CLAMP)
    save(tex); textures[semantic] = tex

path = DEST+'/Materials/M_ZombieDog_RandomWounds'
mat = u.load_asset(path) if LIB.does_asset_exist(path) else TOOLS.create_asset(
    'M_ZombieDog_RandomWounds', DEST+'/Materials', u.Material, u.MaterialFactoryNew())
if LIB.get_metadata_tag(mat, 'ZombieDog.RandomWounds') != '4':
    MEL.delete_all_material_expressions(mat)
    mat.set_editor_property('used_with_skeletal_mesh', True)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_MASKED)
    mat.set_editor_property('opacity_mask_clip_value', .33)

    def node(cls, **properties):
        result = MEL.create_material_expression(mat, cls)
        for key, value in properties.items(): result.set_editor_property(key, value)
        return result

    def connect(src, output, dst, pin):
        if not MEL.connect_material_expressions(src, output, dst, pin):
            raise RuntimeError('Unable to connect '+pin)

    def custom(code, inputs, kind=u.CustomMaterialOutputType.CMOT_FLOAT3):
        result = node(u.MaterialExpressionCustom, code=code, output_type=kind)
        pins = []
        for name in inputs:
            pin = u.CustomInput(); pin.set_editor_property('input_name', name); pins.append(pin)
        result.set_editor_property('inputs', pins)
        for name, (src, output) in inputs.items(): connect(src, output, result, name)
        return result

    def scalar(name, default):
        return node(u.MaterialExpressionScalarParameter, parameter_name=name, default_value=default)

    def vector4(name, default):
        param = node(u.MaterialExpressionVectorParameter, parameter_name=name, default_value=u.LinearColor(*default))
        packed = node(u.MaterialExpressionAppendVector)
        connect(param, 'RGB', packed, 'A'); connect(param, 'A', packed, 'B')
        return packed

    samples = {}
    for semantic, texture in textures.items():
        sampler = (u.MaterialSamplerType.SAMPLERTYPE_NORMAL if semantic.endswith('Normal') else
                   u.MaterialSamplerType.SAMPLERTYPE_COLOR if semantic.endswith('Base') else
                   u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR if semantic == 'RestPosition' else
                   u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        samples[semantic] = node(u.MaterialExpressionTextureSampleParameter2D,
                                parameter_name=semantic, texture=texture, sampler_type=sampler)
    seed = scalar('WoundSeed', 0.)
    fixed = scalar('FixedWound', 0.)
    is_fur = scalar('IsFur', 0.)
    inputs = dict(Rest=(samples['RestPosition'], 'RGB'), Seed=(seed, ''), FixedWound=(fixed, ''))
    for i in range(8):
        for prefix, parameter, default in [('C','WoundCenter',(0,0,0,0)), ('U','WoundU',(1,0,0,1)),
                                           ('V','WoundV',(0,1,0,1)), ('N','WoundN',(0,0,1,1))]:
            inputs[prefix+str(i)] = (vector4(parameter+str(i), default), '')
    mask = custom((PROJECT/'Tools/ZombieDog/random_wound_mask.hlsl').read_text(encoding='utf-8'),
                  inputs, u.CustomMaterialOutputType.CMOT_FLOAT4)
    color = custom('''
float3 tissue = lerp(float3(.052,.004,.003),float3(.20,.030,.018),Mask.z*.45+Mask.w*.55);
float detail = saturate(dot(Skin,float3(.2126,.7152,.0722))*5.5);
tissue *= lerp(.78,1.18,detail);
float3 base = lerp(Coat,Skin,Mask.x);
return lerp(base,tissue,Mask.y);
''', dict(Mask=(mask,''),Coat=(samples['CoatBase'],'RGB'),Skin=(samples['SkinBase'],'RGB')))
    normal = custom('return normalize(lerp(Coat,Skin,Mask.x));',
                    dict(Mask=(mask,''),Coat=(samples['CoatNormal'],'RGB'),Skin=(samples['SkinNormal'],'RGB')))
    roughness = custom('return lerp(lerp(.84,Data.g,Mask.x),.29+Mask.z*.09,Mask.y);',
                       dict(Mask=(mask,''),Data=(samples['SurfaceData'],'RGB')),u.CustomMaterialOutputType.CMOT_FLOAT1)
    alpha = custom('return lerp(1.0,Data.r*(1.0-Mask.x),IsFur);',
                   dict(Mask=(mask,''),Data=(samples['SurfaceData'],'RGB'),IsFur=(is_fur,'')),u.CustomMaterialOutputType.CMOT_FLOAT1)
    for expression, output, prop in [(color,'',u.MaterialProperty.MP_BASE_COLOR),
            (normal,'',u.MaterialProperty.MP_NORMAL),(roughness,'',u.MaterialProperty.MP_ROUGHNESS),
            (alpha,'',u.MaterialProperty.MP_OPACITY_MASK),(samples['SurfaceData'],'B',u.MaterialProperty.MP_AMBIENT_OCCLUSION),
            (scalar('Specular',.32),'',u.MaterialProperty.MP_SPECULAR)]:
        if not MEL.connect_material_property(expression,output,prop):
            raise RuntimeError('Cannot connect output '+str(prop))
    MEL.layout_material_expressions(mat)
    errors = MEL.recompile_material(mat)
    if errors:
        raise RuntimeError('Material compilation failed: '+'\n'.join(errors))
    LIB.set_metadata_tag(mat,'ZombieDog.RandomWounds','4'); save(mat)

materials = {}
for role, fur, fixed in [('Body',0.,0.),('Fur',1.,0.),('EarScar',0.,1.)]:
    name = 'MI_ZombieDog_Random'+role; path = DEST+'/Materials/'+name
    instance = u.load_asset(path) if LIB.does_asset_exist(path) else TOOLS.create_asset(
        name,DEST+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(instance,mat)
    MEL.set_material_instance_scalar_parameter_value(instance,'IsFur',fur)
    MEL.set_material_instance_scalar_parameter_value(instance,'FixedWound',fixed)
    MEL.update_material_instance(instance); save(instance); materials[role] = instance

data = json.loads((ROOT/'wound_surfaces.json').read_text(encoding='utf-8'))
path = DEST+'/DA_ZombieDog_WoundSurfaces'
surface_set = u.load_asset(path) if LIB.does_asset_exist(path) else None
if surface_set is None:
    factory = u.DataAssetFactory(); factory.set_editor_property('data_asset_class',u.ZombieDogWoundSurfaceSet)
    surface_set = TOOLS.create_asset('DA_ZombieDog_WoundSurfaces',DEST,u.ZombieDogWoundSurfaceSet,factory)
surfaces = []
for row in data['surfaces']:
    surface = u.ZombieDogWoundSurface()
    for key in ['a','b','c','normal']: surface.set_editor_property(key,u.Vector(*row[key]))
    surface.set_editor_property('area',row['area']); surface.set_editor_property('region',row['region'])
    surfaces.append(surface)
surface_set.set_editor_property('surfaces',surfaces); save(surface_set)

mesh = duplicate('/Game/Monsters/ZombieDog/FineSkinV3/SK_ZombieDog_FineSkin','SK_ZombieDog_RandomWounds')
slots = mesh.get_editor_property('materials')
for i, slot in enumerate(slots):
    role = 'Fur' if 'Fur' in str(slot.material_slot_name) else 'EarScar' if 'EarScar' in str(slot.material_slot_name) else 'Body'
    slot.material_interface = materials[role]; slots[i] = slot
mesh.set_editor_property('materials',slots); save(mesh)
bp = u.load_asset('/Game/Monsters/ZombieDog/V1/BP_ZombieDog')
u.BlueprintEditorLibrary.compile_blueprint(bp)
defaults = u.get_default_object(bp.generated_class())
previous_set = defaults.get_editor_property('animation_set')
dataset = duplicate(previous_set.get_path_name(),'DA_ZombieDog_RandomWounds')
dataset.set_editor_property('reference_mesh',mesh); save(dataset)
defaults.set_editor_property('animation_set',dataset)
defaults.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
appearance = defaults.get_editor_property('wound_appearance')
appearance.set_editor_property('enabled',True)
appearance.set_editor_property('random_seed',0)
appearance.set_editor_property('min_wounds',3)
appearance.set_editor_property('max_wounds',6)
appearance.set_editor_property('surface_set',surface_set)
LIB.set_metadata_tag(bp,'ZombieDog.Appearance','RandomWoundsV4'); save(bp)
(ROOT/'ue_delivery.json').write_text(json.dumps(dict(blueprint=bp.get_path_name(),
    mesh=mesh.get_path_name(),dataset=dataset.get_path_name(),surface_set=surface_set.get_path_name(),
    previous_dataset=previous_set.get_path_name(),materials={k:v.get_path_name() for k,v in materials.items()},
    component='WoundAppearance',seed_default=0,target_wounds=[3,6],maximum_wound_slots=8,
    surface_triangles=len(surfaces),f6_entry='ZombieDog / 僵尸犬',runtime_tested=False,preview_rendered=False),
    ensure_ascii=False,indent=2),encoding='utf-8')
u.log('ZOMBIE_DOG_RANDOM_WOUNDS_INSTALLED')
