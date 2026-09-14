"""Author 715-only polymer accessories from their original textured surfaces."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
ROOT = O.parents[1]
D = '/Game/Weapons/DanWesson715/AccessoryPolymer20260914'
CHROME = '/Game/Weapons/DanWesson715/Chrome20260914'
SOURCE = '/Game/Weapons/DanWesson715/Attachments20260914/Materials'
L, E = u.MaterialEditingLibrary, u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
receipt = {'parts': {}, 'materials': {}, 'state': 'Authored; no gameplay or visual testing'}

def load(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing authoring source: ' + path)
    return asset

def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())
    return asset

def clone(path, destination):
    return load(destination) if E.does_asset_exist(destination) else E.duplicate_asset(path, destination)

def node(material, cls, **properties):
    value = L.create_material_expression(material, cls)
    for key, prop in properties.items():
        value.set_editor_property(key, prop)
    return value

def wire(source, destination, pin):
    expression, output = source if isinstance(source, tuple) else (source, '')
    if not L.connect_material_expressions(expression, output, destination, pin):
        raise RuntimeError('Cannot connect ' + destination.get_name() + ':' + pin)

def prop(source, name):
    expression, output = source if isinstance(source, tuple) else (source, '')
    if not L.connect_material_property(expression, output, getattr(u.MaterialProperty, 'MP_' + name)):
        raise RuntimeError('Cannot connect ' + name)

def constant(material, value):
    return node(material, u.MaterialExpressionConstant, r=value)

def vector(material, value):
    return node(material, u.MaterialExpressionConstant3Vector, constant=u.LinearColor(*value, 1))

def custom(material, code, inputs, size, description):
    expression = node(material, u.MaterialExpressionCustom, code=code,
        output_type=getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(size)), description=description)
    pins = []
    for name in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    expression.set_editor_property('inputs', pins)
    for name, source in inputs.items():
        wire(source, expression, name)
    return expression

def body(kind):
    label = 'Holographic' if kind == 'holographic' else kind
    source = SOURCE + '/M_DW715_' + label + '_Body'
    material = clone(source, D + '/Materials/M_DW715_Polymer_' + label)
    if not E.get_metadata_tag(material, 'DW715OwnPolymer'):
        color = L.get_material_property_input_node(material, u.MaterialProperty.MP_BASE_COLOR)
        rough = L.get_material_property_input_node(material, u.MaterialProperty.MP_ROUGHNESS)
        metal = L.get_material_property_input_node(material, u.MaterialProperty.MP_METALLIC)
        if not all(isinstance(n, u.MaterialExpressionLinearInterpolate) for n in (color, rough, metal)):
            raise RuntimeError('Original regional finish graph changed: ' + source)
        # A is the device's own UV0 texture/material. B was the gun's UV1 coat.
        # Restore the original color including markings, and make the former
        # coated exterior dielectric/matte. Existing aperture masks stay intact.
        wire(constant(material, 0), color, 'Alpha')
        wire(constant(material, .56), rough, 'B')
        wire(constant(material, 0), metal, 'B')
        E.set_metadata_tag(material, 'DW715OwnPolymer', '1')
        E.set_metadata_tag(material, 'PolymerSource', source)
        E.set_metadata_tag(material, 'WeaponFinishRegion', 'Own UV0 color/normal/AO; exterior polymer; optics and markings retained')
        L.recompile_material(material)
        save(material)
    receipt['materials'][kind] = {'source': source, 'dry': material.get_path_name(), 'exterior_roughness': .56, 'exterior_metallic': 0}
    return material

def mount():
    path = D + '/Materials/M_DW715_Polymer_Mount'
    material = load(path) if E.does_asset_exist(path) else A.create_asset('M_DW715_Polymer_Mount', D + '/Materials', u.Material, u.MaterialFactoryNew())
    if not E.get_metadata_tag(material, 'DW715OwnPolymer'):
        prop(vector(material, (.022, .025, .030)), 'BASE_COLOR')
        prop(constant(material, .56), 'ROUGHNESS')
        prop(constant(material, 0), 'METALLIC')
        prop(constant(material, .5), 'SPECULAR')
        E.set_metadata_tag(material, 'DW715OwnPolymer', '1')
        L.recompile_material(material)
        save(material)
    return material

def wet_material(dry, kind):
    wet = clone(dry.get_path_name(), D + '/Materials/' + dry.get_name() + '_Wet')
    if not E.get_metadata_tag(wet, 'DW715PolymerRain'):
        original = {}
        for name in ('BASE_COLOR', 'ROUGHNESS', 'NORMAL'):
            key = getattr(u.MaterialProperty, 'MP_' + name)
            source = L.get_material_property_input_node(wet, key)
            original[name] = (source, L.get_material_property_input_node_output_name(wet, key)) if source else vector(wet, (0, 0, 1))
        amount = node(wet, u.MaterialExpressionScalarParameter, parameter_name='WeaponWetness', default_value=0)
        if kind in ('laser', 'flashlight'):
            mask = (node(wet, u.MaterialExpressionVertexColor), 'R')
        elif kind == 'holographic':
            # Use the original exterior mask, not the new zero metallic output.
            rough = original['ROUGHNESS'][0]
            mask = L.get_inputs_for_material_expression(wet, rough)[2]
        else:
            mask = constant(wet, 1)
        amount = custom(wet, 'return Wet*saturate(Exterior);', {'Wet': amount, 'Exterior': mask}, 1, 'Polymer exterior rain mask')
        beads = custom(wet, (ROOT/'SourceAssets/WeatherNatural20260912/WeaponBeads.hlsl').read_text(),
            {'UV': node(wet, u.MaterialExpressionTextureCoordinate), 'Wet': amount}, 4, 'Polymer rain beads')
        prop(custom(wet, 'return Base*(1-Data.a*.07);', {'Base': original['BASE_COLOR'], 'Data': beads}, 3, 'Wet polymer color'), 'BASE_COLOR')
        prop(custom(wet, 'return lerp(lerp(Base,max(.18,Base*.70),Data.a),.065,Data.b*.8);',
            {'Base': original['ROUGHNESS'], 'Data': beads}, 1, 'Wet polymer roughness'), 'ROUGHNESS')
        prop(custom(wet, 'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.35)+Data.xy,Base.z));',
            {'Base': original['NORMAL'], 'Data': beads}, 3, 'Wet polymer normal'), 'NORMAL')
        E.set_metadata_tag(wet, 'DW715PolymerRain', '1')
        L.recompile_material(wet)
        save(wet)
    return wet

mount_material = mount()
dry_materials = {kind: body(kind) for kind in ('laser', 'flashlight', 'holographic')}
dry_materials['mount'] = mount_material
new_wet = {dry.get_path_name(): wet_material(dry, kind) for kind, dry in dry_materials.items()}
for kind in ('laser', 'flashlight', 'holographic'):
    suffix = '/Meshes/SM_DW715_holographic' if kind == 'holographic' else '/' + kind + '/SM_TacticalDevice'
    source = CHROME + '/Attachments' + suffix
    mesh = clone(source, D + '/Attachments' + suffix)
    slots = mesh.get_editor_property('static_materials')
    for i, slot in enumerate(slots):
        label = str(slot.material_slot_name)
        if label in ('Holosight', 'M_Tactical_laser', 'M_Tactical_flashlight'):
            slot.material_interface = dry_materials[kind]
        elif label in ('DW715_AdapterSteel', 'M_Tactical_Collar'):
            slot.material_interface = mount_material
        slots[i] = slot
    mesh.set_editor_property('static_materials', slots)
    E.set_metadata_tag(mesh, 'DW715OwnPolymer', 'Own accessory exterior; Chrome weapon retained')
    save(mesh)
    receipt['parts'][kind] = {'mesh': mesh.get_path_name(), 'source': source,
        'slots': {str(s.material_slot_name): s.material_interface.get_path_name() for s in slots}}
    u.log('DW715_POLYMER_PART_SAVED ' + kind)

library = clone(CHROME + '/DA_DW715_WetMaterials', D + '/DA_DW715_WetMaterials')
mapping = dict(library.get_editor_property('wet_materials'))
mapping.update(new_wet)
library.set_editor_property('wet_materials', mapping)
save(library)
receipt['weather_additions'] = library.get_path_name()
receipt['new_wet_materials'] = {dry: wet.get_path_name() for dry, wet in new_wet.items()}
(O/'import.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('DW715_ACCESSORY_POLYMER_IMPORT_COMPLETE')
