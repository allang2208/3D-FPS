"""Patch surface inputs only, preserving existing color/opacity/SSS/emission."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
BASE = '/Game/Weapons/ApprenticeStaff20260927'
P = json.loads((ROOT/'parameters.json').read_text(encoding='utf-8'))
L = u.MaterialEditingLibrary
TAG = 'ElementPolishV42:'


def material_path(kind):
    version = P['heads'][kind]['version']
    return f'{BASE}/ElementHeadsV{version}/Materials/M_StaffCraft_{kind}_V{version}'


def apply_surface(material,kind):
    config = P['heads'][kind]
    # Repeatable authoring: replace only this revision's own surface nodes.
    for expression in list(L.get_material_expressions(material)):
        if str(expression.get_editor_property('desc')).startswith(TAG):
            L.delete_material_expression(material,expression)
    count = 0

    def node(cls,label,**props):
        nonlocal count
        result = L.create_material_expression(material,cls,-1400+(count%5)*240,1300+(count//5)*230)
        count += 1
        result.set_editor_property('desc',TAG+label)
        for key,value in props.items():
            result.set_editor_property(key,value)
        return result

    def parameter(name,value):
        return node(u.MaterialExpressionScalarParameter,name,parameter_name=name,default_value=float(value))

    def texture(channel):
        version = config['version']
        name = f'T_StaffCraft_{kind}_{channel}_V{version}'
        for expression in L.get_material_expressions(material):
            if isinstance(expression,u.MaterialExpressionTextureSample):
                asset = expression.get_editor_property('texture')
                if asset and asset.get_name()==name:
                    return expression
        asset = u.load_asset(f'{BASE}/ElementHeadsV{version}/Textures/{name}')
        if not asset:
            raise RuntimeError('Missing retained elemental texture '+name)
        return node(u.MaterialExpressionTextureSample,name,texture=asset,
                    sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal'
                    else u.MaterialSamplerType.SAMPLERTYPE_MASKS)

    def custom(label,code,inputs,width=1):
        result = node(u.MaterialExpressionCustom,label,code=code,
                      output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
        pins=[]
        for name in inputs:
            pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
        result.set_editor_property('inputs',pins)
        for name,source in inputs.items():
            if not L.connect_material_expressions(source,'',result,name):
                raise RuntimeError('Cannot connect elemental surface '+name)
        return result

    if kind=='Magma':
        roughness = custom('cooled crust and molten channel contrast',
            'return lerp(Crust,Molten,saturate(Packed.b*HeatGain));',
            dict(Packed=texture('RGE'),Crust=parameter('CrustRoughness',config['crust_roughness']),
                 Molten=parameter('MoltenRoughness',config['molten_roughness']),
                 HeatGain=parameter('HeatMaskGain',config['heat_mask_gain'])))
        normal = custom('restrained rock relief',
            'return normalize(float3(Surface.xy*Strength,lerp(1.0,Surface.z,Strength)));',
            dict(Surface=texture('Normal'),Strength=parameter('RockNormalStrength',config['normal_strength'])),3)
    else:
        normal = node(u.MaterialExpressionConstant3Vector,'clean geometric surface',constant=u.LinearColor(0,0,1,1))
        if kind=='Jade':
            roughness = custom('coherent mineral polish',
                'return lerp(Low,High,saturate((Packed.r-0.125)/0.12));',
                dict(Packed=texture('RGE'),Low=parameter('JadeRoughnessMin',config['roughness_min']),
                     High=parameter('JadeRoughnessMax',config['roughness_max'])))
        else:
            roughness = parameter('FacetRoughness',config['roughness'])
    if not L.connect_material_property(roughness,'',u.MaterialProperty.MP_ROUGHNESS):
        raise RuntimeError('Cannot connect elemental roughness')
    if not L.connect_material_property(normal,'',u.MaterialProperty.MP_NORMAL):
        raise RuntimeError('Cannot connect elemental normal')
    material.set_editor_property('forward_blends_sky_light_cubemaps',True)
    if kind=='Storm':
        material.set_editor_property('screen_space_reflections',config['screen_space_reflections'])
        material.set_editor_property('allow_front_layer_translucency',True)
    return material


def apply_installed_surface(material):
    """Called before saving an older V37/V38 rebuilt material at its stable path."""
    receipt = ROOT/'install-receipt.json'
    if not receipt.exists():
        return
    installed = json.loads(receipt.read_text(encoding='utf-8'))
    if not (installed.get('complete') and installed.get('active')):
        return
    path = material.get_path_name().split('.')[0]
    for kind in P['heads']:
        if path==material_path(kind):
            apply_surface(material,kind)
            return
