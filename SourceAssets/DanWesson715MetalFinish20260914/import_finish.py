"""Import four refined metal surfaces and bind a dedicated accepted-mesh copy."""
import ast
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
ROOT = O.parents[1]
D = '/Game/Weapons/DanWesson715/MetalFinish20260914'
SOURCE = '/Game/Weapons/DanWesson715/Upgrade20260914/SK_DW715_Manny'
A = u.AssetToolsHelpers.get_asset_tools()
L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
manifest = json.loads((O / 'textures.json').read_text())
materials, receipt = {}, {'materials': {}, 'textures': {}, 'source_mesh': SOURCE}

def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Unable to save ' + asset.get_path_name())
    return asset

for group, info in manifest.items():
    name = info['material']
    path = D + '/Materials/' + name
    m = u.load_asset(path) if E.does_asset_exist(path) else A.create_asset(name, D + '/Materials', u.Material, u.MaterialFactoryNew())
    L.delete_all_material_expressions(m)
    L.set_material_usage(m, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    maps = {}
    for kind, filename in info['textures'].items():
        task = u.AssetImportTask()
        task.filename, task.destination_path, task.destination_name = filename, D + '/Textures', Path(filename).stem
        task.automated, task.replace_existing, task.save = True, True, False
        A.import_asset_tasks([task])
        tex = u.load_asset(task.destination_path + '/' + task.destination_name)
        if not tex:
            raise RuntimeError('Texture import failed: ' + filename)
        tex.set_editor_property('srgb', kind == 'BaseColor')
        tex.set_editor_property('lod_bias', 0)
        tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if kind == 'Normal' else u.TextureGroup.TEXTUREGROUP_WEAPON)
        # BC7 avoids DXT1 block quantization of shallow roughness variation and
        # engraving contrast; the tangent normals retain dedicated BC5 storage.
        tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP if kind == 'Normal' else u.TextureCompressionSettings.TC_BC7)
        tex.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
        if kind == 'Normal':
            tex.set_editor_property('flip_green_channel', True)
        save(tex)
        node = L.create_material_expression(m, u.MaterialExpressionTextureSample)
        node.set_editor_property('texture', tex)
        node.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind == 'Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind == 'BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        if kind == 'BaseColor':
            L.connect_material_property(node, 'RGB', u.MaterialProperty.MP_BASE_COLOR)
        elif kind == 'Normal':
            L.connect_material_property(node, 'RGB', u.MaterialProperty.MP_NORMAL)
        else:
            for channel, prop in [('R', u.MaterialProperty.MP_AMBIENT_OCCLUSION), ('G', u.MaterialProperty.MP_ROUGHNESS), ('B', u.MaterialProperty.MP_METALLIC)]:
                L.connect_material_property(node, channel, prop)
        maps[kind] = tex.get_path_name()
    E.set_metadata_tag(m, 'DW715MetalFinish', 'Satin stainless; UV0 HeroUV; baked object-space grain; geometry/rig preserved')
    L.recompile_material(m)
    save(m)
    materials[info['slot']] = m
    receipt['materials'][group], receipt['textures'][group] = m.get_path_name(), maps
    u.log('DW715_FINISH_MATERIAL_IMPORTED ' + group)

# Reuse the accepted mesh's actual render data, split normals, UV0, skinning,
# skeleton and nonmetal/hand materials. No geometry or animation reimport.
mesh_path = D + '/SK_DW715_Manny'
mesh = u.load_asset(mesh_path) if E.does_asset_exist(mesh_path) else E.duplicate_asset(SOURCE, mesh_path)
slots = mesh.get_editor_property('materials')
for i, slot in enumerate(slots):
    key = str(slot.material_slot_name)
    if key in materials:
        slot.material_interface = materials[key]
        slots[i] = slot
mesh.set_editor_property('materials', slots)
E.set_metadata_tag(mesh, 'DW715MetalFinishSource', SOURCE)
save(mesh)

# Extend the existing shared weather registries, keeping all other entries.
unreal, LIB, TOOLS, DEST, REPORT = u, L, A, D + '/Materials', {'materials': []}
tree = ast.parse((ROOT / 'Tools/Weather/build_natural_weather.py').read_text(encoding='utf-8'))
helpers = {'node', 'wire', 'prop', 'scalar', 'constant', 'vector', 'custom'}
exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name in helpers], type_ignores=[]), 'existing_weather_graph_helpers', 'exec'))
wetmaps = {}
for dry in materials.values():
    path = D + '/Materials/' + dry.get_name() + '_Wet'
    wet = u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(dry.get_path_name(), path)
    if not E.get_metadata_tag(wet, 'DW715MetalFinishWet'):
        original = {}
        for pname in ['BASE_COLOR', 'ROUGHNESS', 'NORMAL']:
            propid = getattr(u.MaterialProperty, 'MP_' + pname)
            original[pname] = (L.get_material_property_input_node(wet, propid), L.get_material_property_input_node_output_name(wet, propid))
        beads = custom(wet, (ROOT / 'SourceAssets/WeatherNatural20260912/WeaponBeads.hlsl').read_text(), dict(UV=node(wet, u.MaterialExpressionTextureCoordinate), Wet=scalar(wet, 'WeaponWetness', 0)), 4, 'WeatherBeads')
        prop(custom(wet, 'return Base*(1-Data.a*.07);', dict(Base=original['BASE_COLOR'], Data=beads), 3), 'BASE_COLOR')
        prop(custom(wet, 'return lerp(lerp(Base,max(.085,Base*.70),Data.a),.065,Data.b*.8);', dict(Base=original['ROUGHNESS'], Data=beads), 1), 'ROUGHNESS')
        prop(custom(wet, 'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.35)+Data.xy,Base.z));', dict(Base=original['NORMAL'], Data=beads), 3), 'NORMAL')
        E.set_metadata_tag(wet, 'DW715MetalFinishWet', '1')
        L.set_material_usage(wet, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        L.recompile_material(wet)
        save(wet)
    wetmaps[dry.get_path_name()] = wet
for path in ['/Game/Weather/RainVisibility/DA_WeatherPresentation', '/Game/Weather/NaturalV2/DA_WeatherPresentation']:
    library = u.load_asset(path)
    mapping = dict(library.get_editor_property('wet_materials'))
    mapping.update(wetmaps)
    library.set_editor_property('wet_materials', mapping)
    save(library)
receipt.update(mesh=mesh.get_path_name(), skeleton=mesh.skeleton.get_path_name(),
               material_slots={str(slot.material_slot_name): slot.material_interface.get_path_name() for slot in slots},
               wet_materials={key: wet.get_path_name() for key, wet in wetmaps.items()},
               state='Imported and saved. No preview, runtime or gameplay testing.')
(O / 'import.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('DW715_METAL_FINISH_IMPORT_COMPLETE')
