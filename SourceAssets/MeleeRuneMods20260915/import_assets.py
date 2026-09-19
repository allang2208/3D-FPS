"""Author the three rune textures, option icons and additive surface material."""
import json
from pathlib import Path
import unreal as ue

root = Path(__file__).resolve().parent
dest = '/Game/Weapons/MeleeRunes20260915'
icons = '/Game/ColdSteelData/AttachmentIcons20260913'
tools = ue.AssetToolsHelpers.get_asset_tools()
L = ue.MaterialEditingLibrary
keys = ('resonance_rune', 'erosion_rune', 'conduction_rune')
textures = {}
for key in keys:
    for folder, name, icon in ((dest, 'T_'+key, False), (icons, 'blade_2_'+key, True)):
        task = ue.AssetImportTask()
        task.filename = str(root/'Generated'/(key+'.png'))
        task.destination_path = folder
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = False
        tools.import_asset_tasks([task])
        texture = ue.load_asset(folder+'/'+name)
        if texture is None:
            raise RuntimeError('Import failed: '+name)
        texture.srgb = bool(icon)
        texture.address_x = ue.TextureAddress.TA_CLAMP
        texture.address_y = ue.TextureAddress.TA_CLAMP
        texture.lod_group = ue.TextureGroup.TEXTUREGROUP_UI if icon else ue.TextureGroup.TEXTUREGROUP_EFFECTS
        texture.compression_settings = ue.TextureCompressionSettings.TC_EDITOR_ICON if icon else ue.TextureCompressionSettings.TC_DEFAULT
        texture.mip_gen_settings = ue.TextureMipGenSettings.TMGS_NO_MIPMAPS if icon else ue.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE
        ue.EditorAssetLibrary.set_metadata_tag(texture, 'Source', 'Built-in image_gen, user-requested silver-white sword runes, 2026-09-15. Original and prompt retained in SourceAssets/MeleeRuneMods20260915.')
        ue.EditorAssetLibrary.save_loaded_asset(texture, False)
        if not icon:
            textures[key] = texture

material = ue.load_asset(dest+'/M_SilverRuneSurface')
if material is None:
    material = tools.create_asset('M_SilverRuneSurface', dest, ue.Material, ue.MaterialFactoryNew())
L.delete_all_material_expressions(material)
material.set_editor_property('blend_mode', ue.BlendMode.BLEND_ADDITIVE)
material.set_editor_property('shading_model', ue.MaterialShadingModel.MSM_UNLIT)
material.set_editor_property('two_sided', False)
L.set_material_usage(material, ue.MaterialUsage.MATUSAGE_SKELETAL_MESH)

def node(cls, **props):
    n = L.create_material_expression(material, cls)
    for k,v in props.items():
        n.set_editor_property(k,v)
    return n
def link(a, pin, b, target):
    if target == 'Input':
        target = str(L.get_material_expression_input_names(b)[0])
    if not L.connect_material_expressions(a,pin,b,target):
        raise RuntimeError('Cannot connect '+target)
def scalar(name,value):
    return node(ue.MaterialExpressionScalarParameter, parameter_name=name, default_value=value)
def vector(name,value):
    return node(ue.MaterialExpressionVectorParameter, parameter_name=name, default_value=ue.LinearColor(*value))

position = node(ue.MaterialExpressionLocalPosition, local_origin=ue.LocalPositionOrigin.PRIMITIVE,
                included_offsets=ue.PositionIncludedOffsets.EXCLUDE_OFFSETS)
normal = node(ue.MaterialExpressionVertexNormalWS)
normal_local = node(ue.MaterialExpressionTransform,
                    transform_source_type=ue.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,
                    transform_type=ue.MaterialVectorCoordTransform.TRANSFORM_LOCAL)
link(normal,'',normal_local,'Input')
interpolated_normal = node(ue.MaterialExpressionVertexInterpolator)
link(normal_local,'',interpolated_normal,'Input')
texture_node = node(ue.MaterialExpressionTextureObjectParameter, parameter_name='RuneTexture',
                    texture=textures['resonance_rune'], sampler_type=ue.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
inputs = {
    'P': (position,''), 'N': (interpolated_normal,''),
    'BladeOrigin': (vector('BladeOrigin',(0,0,0,0)),'RGB'),
    'BladeAxis': (vector('BladeAxis',(0,0,1,0)),'RGB'),
    'Dimensions': (vector('Dimensions',(12,10,63,0)),'RGB'),
    'RuneTexture': (texture_node,''), 'RuneMode': (scalar('RuneMode',-1),''),
    'T': (node(ue.MaterialExpressionTime),''),
    'PreviewTime': (scalar('PreviewTime',-1),''),
    'GlowStrength': (scalar('GlowStrength',5),'')
}
pins=[]
for name in inputs:
    pin=ue.CustomInput()
    pin.set_editor_property('input_name',name)
    pins.append(pin)
custom=node(ue.MaterialExpressionCustom, code=(root/'silver_runes.hlsl').read_text(encoding='utf-8'),
            output_type=ue.CustomMaterialOutputType.CMOT_FLOAT4,inputs=pins,description='Silver-white animated blade-surface runes')
for name,(n,pin) in inputs.items():
    link(n,pin,custom,name)
rgb=node(ue.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False)
alpha=node(ue.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
link(custom,'',rgb,'Input')
link(custom,'',alpha,'Input')
L.connect_material_property(rgb,'',ue.MaterialProperty.MP_EMISSIVE_COLOR)
L.connect_material_property(alpha,'',ue.MaterialProperty.MP_OPACITY)
L.layout_material_expressions(material)
L.recompile_material(material)
ue.EditorAssetLibrary.save_loaded_asset(material,False)
(root/'import_receipt.json').write_text(json.dumps({'material':material.get_path_name(),'textures':{k:t.get_path_name() for k,t in textures.items()}},indent=2),encoding='utf-8')
ue.log('MELEE_RUNE_ASSETS_AUTHORED')
